package main

import (
	"context"
	"database/sql"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"syscall"
	"time"

	_ "github.com/lib/pq"
	_ "modernc.org/sqlite"
	"rsc.io/qr"

	"bytes"

	"go.mau.fi/whatsmeow"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/store"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
)

// Message represents a chat message for our client
type Message struct {
	ID          string    `json:"id"`
	ChatJID     string    `json:"chat_jid"`
	TenantID    string    `json:"tenant_id"`
	Time        time.Time `json:"timestamp"`
	Sender      string    `json:"sender"`
	Content     string    `json:"content"`
	IsFromMe    bool      `json:"is_from_me"`
	MediaType   string    `json:"media_type"`
	Filename    string    `json:"filename"`
	BusinessJID string    `json:"business_jid"`
}

// QR Code storage for REST API
var (
	latestQRPNG []byte
	qrMutex     sync.Mutex
)

type QRResponse struct {
	Success bool   `json:"success"`
	QR      string `json:"qr,omitempty"`
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
}

// Database handler for storing message history
type MessageStore struct {
	db *sql.DB
}

func getDefaultTenantID() string {
	defaultTenantID := os.Getenv("DEFAULT_TENANT_ID")
	if defaultTenantID == "" {
		defaultTenantID = "default"
	}
	return defaultTenantID
}

func tableExists(db *sql.DB, tableName string) (bool, error) {
	var name string
	err := db.QueryRow("SELECT name FROM sqlite_master WHERE type='table' AND name=?", tableName).Scan(&name)
	if err == sql.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return name == tableName, nil
}

func columnExists(db *sql.DB, tableName string, columnName string) (bool, error) {
	rows, err := db.Query(fmt.Sprintf("PRAGMA table_info(%s)", tableName))
	if err != nil {
		return false, err
	}
	defer rows.Close()

	for rows.Next() {
		var cid int
		var name, columnType string
		var notNull, pk int
		var defaultValue sql.NullString
		if err := rows.Scan(&cid, &name, &columnType, &notNull, &defaultValue, &pk); err != nil {
			return false, err
		}
		if name == columnName {
			return true, nil
		}
	}
	return false, nil
}

func migrateChatsTable(db *sql.DB, defaultTenantID string) error {
	_, err := db.Exec("ALTER TABLE chats RENAME TO chats_old")
	if err != nil {
		return err
	}

	_, err = db.Exec(`
		CREATE TABLE chats (
			jid TEXT,
			tenant_id TEXT,
			name TEXT,
			last_message_time TIMESTAMP,
			PRIMARY KEY (jid, tenant_id)
		);
	`)
	if err != nil {
		return err
	}

	_, err = db.Exec(
		"INSERT INTO chats (jid, tenant_id, name, last_message_time) SELECT jid, ?, name, last_message_time FROM chats_old",
		defaultTenantID,
	)
	if err != nil {
		return err
	}

	_, err = db.Exec("DROP TABLE chats_old")
	return err
}

func migrateMessagesTable(db *sql.DB, defaultTenantID string) error {
	_, err := db.Exec("ALTER TABLE messages RENAME TO messages_old")
	if err != nil {
		return err
	}

	_, err = db.Exec(`
		CREATE TABLE messages (
			id TEXT,
			chat_jid TEXT,
			tenant_id TEXT,
			sender TEXT,
			content TEXT,
			timestamp TIMESTAMP,
			is_from_me BOOLEAN,
			media_type TEXT,
			filename TEXT,
			url TEXT,
			media_key BLOB,
			file_sha256 BLOB,
			file_enc_sha256 BLOB,
			file_length INTEGER,
			PRIMARY KEY (id, chat_jid, tenant_id),
			FOREIGN KEY (chat_jid, tenant_id) REFERENCES chats(jid, tenant_id)
		);
	`)
	if err != nil {
		return err
	}

	_, err = db.Exec(
		`INSERT INTO messages (
			id, chat_jid, tenant_id, sender, content, timestamp, is_from_me,
			media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length
		) SELECT
			id, chat_jid, ?, sender, content, timestamp, is_from_me,
			media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length
		FROM messages_old`,
		defaultTenantID,
	)
	if err != nil {
		return err
	}

	_, err = db.Exec("DROP TABLE messages_old")
	return err
}

func ensureTenantColumns(db *sql.DB) error {
	defaultTenantID := getDefaultTenantID()
	_, _ = db.Exec("PRAGMA foreign_keys=OFF")
	chatsExists, err := tableExists(db, "chats")
	if err != nil {
		return err
	}
	if chatsExists {
		hasTenantID, err := columnExists(db, "chats", "tenant_id")
		if err != nil {
			return err
		}
		if !hasTenantID {
			if err := migrateChatsTable(db, defaultTenantID); err != nil {
				return err
			}
		}
	}

	messagesExists, err := tableExists(db, "messages")
	if err != nil {
		return err
	}
	if messagesExists {
		hasTenantID, err := columnExists(db, "messages", "tenant_id")
		if err != nil {
			return err
		}
		if !hasTenantID {
			if err := migrateMessagesTable(db, defaultTenantID); err != nil {
				return err
			}
		}
	}

	_, _ = db.Exec("PRAGMA foreign_keys=ON")
	return nil
}

// Initialize message store
func NewMessageStore() (*MessageStore, error) {
	// Get database path from environment variable, default to "store/messages.db"
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "store/messages.db"
	}

	// Extract directory from path and create if it doesn't exist
	dbDir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dbDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create database directory %s: %v", dbDir, err)
	}

	// Open SQLite database for messages - USE DELETE MODE (not WAL) for immediate consistency
	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?_pragma=foreign_keys(1)&_pragma=journal_mode(DELETE)&_pragma=busy_timeout(5000)&_pragma=synchronous(FULL)", dbPath))
	if err != nil {
		return nil, fmt.Errorf("failed to open message database: %v", err)
	}

	if err := ensureTenantColumns(db); err != nil {
		return nil, fmt.Errorf("failed to migrate message database: %v", err)
	}

	// Create tables if they don't exist
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS chats (
			jid TEXT,
			tenant_id TEXT,
			name TEXT,
			last_message_time TIMESTAMP,
			PRIMARY KEY (jid, tenant_id)
		);

		CREATE TABLE IF NOT EXISTS messages (
			id TEXT,
			chat_jid TEXT,
			tenant_id TEXT,
			sender TEXT,
			content TEXT,
			timestamp TIMESTAMP,
			is_from_me BOOLEAN,
			media_type TEXT,
			filename TEXT,
			url TEXT,
			media_key BLOB,
			file_sha256 BLOB,
			file_enc_sha256 BLOB,
			file_length INTEGER,
			PRIMARY KEY (id, chat_jid, tenant_id),
			FOREIGN KEY (chat_jid, tenant_id) REFERENCES chats(jid, tenant_id)
		);

		CREATE TABLE IF NOT EXISTS sessions (
			tenant_id TEXT PRIMARY KEY,
			jid TEXT
		);
	`)
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create tables: %v", err)
	}

	return &MessageStore{db: db}, nil
}

// Close the database connection
func (store *MessageStore) Close() error {
	return store.db.Close()
}

// Store a chat in the database
func (store *MessageStore) StoreChat(jid, tenantID, name string, lastMessageTime time.Time) error {
	_, err := store.db.Exec(
		"INSERT OR REPLACE INTO chats (jid, tenant_id, name, last_message_time) VALUES (?, ?, ?, ?)",
		jid, tenantID, name, lastMessageTime,
	)
	return err
}

// Store a message in the database
func (store *MessageStore) StoreMessage(id, chatJID, tenantID, sender, content string, timestamp time.Time, isFromMe bool,
	mediaType, filename, url string, mediaKey, fileSHA256, fileEncSHA256 []byte, fileLength uint64) error {
	// Only store if there's actual content or media
	if content == "" && mediaType == "" {
		return nil
	}

	_, err := store.db.Exec(
		`INSERT OR REPLACE INTO messages
		(id, chat_jid, tenant_id, sender, content, timestamp, is_from_me, media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		id, chatJID, tenantID, sender, content, timestamp, isFromMe, mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength,
	)

	return err
}

// Get messages from a chat
func (store *MessageStore) GetMessages(chatJID, tenantID string, limit int) ([]Message, error) {
	rows, err := store.db.Query(
		"SELECT id, chat_jid, tenant_id, sender, content, timestamp, is_from_me, media_type, filename FROM messages WHERE chat_jid = ? AND tenant_id = ? ORDER BY timestamp DESC LIMIT ?",
		chatJID, tenantID, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []Message
	for rows.Next() {
		var msg Message
		var timestamp time.Time
		err := rows.Scan(&msg.ID, &msg.ChatJID, &msg.TenantID, &msg.Sender, &msg.Content, &timestamp, &msg.IsFromMe, &msg.MediaType, &msg.Filename)
		if err != nil {
			return nil, err
		}
		msg.Time = timestamp
		messages = append(messages, msg)
	}

	return messages, nil
}

// Get all chats
func (store *MessageStore) GetChats() (map[string]time.Time, error) {
	rows, err := store.db.Query("SELECT jid, last_message_time FROM chats ORDER BY last_message_time DESC")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	chats := make(map[string]time.Time)
	for rows.Next() {
		var jid string
		var lastMessageTime time.Time
		err := rows.Scan(&jid, &lastMessageTime)
		if err != nil {
			return nil, err
		}
		chats[jid] = lastMessageTime
	}

	return chats, nil
}

// Extract text content from a message
func extractTextContent(msg *waProto.Message) string {
	if msg == nil {
		return ""
	}

	// Try multiple ways to get text content
	if text := msg.GetConversation(); text != "" {
		return text
	}

	if extendedText := msg.GetExtendedTextMessage(); extendedText != nil {
		if text := extendedText.GetText(); text != "" {
			return text
		}
	}

	// Try image caption
	if imageMsg := msg.GetImageMessage(); imageMsg != nil {
		if caption := imageMsg.GetCaption(); caption != "" {
			return caption
		}
	}

	// Try video caption
	if videoMsg := msg.GetVideoMessage(); videoMsg != nil {
		if caption := videoMsg.GetCaption(); caption != "" {
			return caption
		}
	}

	// Try document caption
	if docMsg := msg.GetDocumentMessage(); docMsg != nil {
		if caption := docMsg.GetCaption(); caption != "" {
			return caption
		}
	}

	// For now, we're ignoring other non-text messages
	return ""
}

// SendMessageResponse represents the response for the send message API
type SendMessageResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// SendMessageRequest represents the request body for the send message API
type SendMessageRequest struct {
	TenantID  string `json:"tenant_id"`
	Recipient string `json:"recipient"`
	Message   string `json:"message"`
	MediaPath string `json:"media_path,omitempty"`
}

// Function to send a WhatsApp message
func sendWhatsAppMessage(client *whatsmeow.Client, recipient string, message string, mediaPath string) (bool, string) {
	if !client.IsConnected() {
		return false, "Not connected to WhatsApp"
	}

	// Create JID for recipient
	var recipientJID types.JID
	var err error

	// Check if recipient is a JID
	isJID := strings.Contains(recipient, "@")

	if isJID {
		// Parse the JID string
		recipientJID, err = types.ParseJID(recipient)
		if err != nil {
			return false, fmt.Sprintf("Error parsing JID: %v", err)
		}
	} else {
		// Create JID from phone number
		recipientJID = types.JID{
			User:   recipient,
			Server: "s.whatsapp.net", // For personal chats
		}
	}

	msg := &waProto.Message{}

	// Check if we have media to send
	if mediaPath != "" {
		// Read media file
		mediaData, err := os.ReadFile(mediaPath)
		if err != nil {
			return false, fmt.Sprintf("Error reading media file: %v", err)
		}

		// Determine media type and mime type based on file extension
		fileExt := strings.ToLower(mediaPath[strings.LastIndex(mediaPath, ".")+1:])
		var mediaType whatsmeow.MediaType
		var mimeType string

		// Handle different media types
		switch fileExt {
		// Image types
		case "jpg", "jpeg":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/jpeg"
		case "png":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/png"
		case "gif":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/gif"
		case "webp":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/webp"

		// Audio types
		case "ogg":
			mediaType = whatsmeow.MediaAudio
			mimeType = "audio/ogg; codecs=opus"

		// Video types
		case "mp4":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/mp4"
		case "avi":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/avi"
		case "mov":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/quicktime"

		// Document types (for any other file type)
		default:
			mediaType = whatsmeow.MediaDocument
			mimeType = "application/octet-stream"
		}

		// Upload media to WhatsApp servers
		resp, err := client.Upload(context.Background(), mediaData, mediaType)
		if err != nil {
			return false, fmt.Sprintf("Error uploading media: %v", err)
		}

		fmt.Println("Media uploaded", resp)

		// Create the appropriate message type based on media type
		switch mediaType {
		case whatsmeow.MediaImage:
			msg.ImageMessage = &waProto.ImageMessage{
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		case whatsmeow.MediaAudio:
			// Handle ogg audio files
			var seconds uint32 = 30 // Default fallback
			var waveform []byte = nil

			// Try to analyze the ogg file
			if strings.Contains(mimeType, "ogg") {
				analyzedSeconds, analyzedWaveform, err := analyzeOggOpus(mediaData)
				if err == nil {
					seconds = analyzedSeconds
					waveform = analyzedWaveform
				} else {
					return false, fmt.Sprintf("Failed to analyze Ogg Opus file: %v", err)
				}
			} else {
				fmt.Printf("Not an Ogg Opus file: %s\n", mimeType)
			}

			msg.AudioMessage = &waProto.AudioMessage{
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
				Seconds:       proto.Uint32(seconds),
				PTT:           proto.Bool(true),
				Waveform:      waveform,
			}
		case whatsmeow.MediaVideo:
			msg.VideoMessage = &waProto.VideoMessage{
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		case whatsmeow.MediaDocument:
			msg.DocumentMessage = &waProto.DocumentMessage{
				Title:         proto.String(mediaPath[strings.LastIndex(mediaPath, "/")+1:]),
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		}
	} else {
		msg.Conversation = proto.String(message)
	}

	// Send message with timeout to prevent deadlock
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	_, err = client.SendMessage(ctx, recipientJID, msg)

	if err != nil {
		return false, fmt.Sprintf("Error sending message: %v", err)
	}

	return true, fmt.Sprintf("Message sent to %s", recipient)
}

// Extract media info from a message
func extractMediaInfo(msg *waProto.Message) (mediaType string, filename string, url string, mediaKey []byte, fileSHA256 []byte, fileEncSHA256 []byte, fileLength uint64) {
	if msg == nil {
		return "", "", "", nil, nil, nil, 0
	}

	// Check for image message
	if img := msg.GetImageMessage(); img != nil {
		return "image", "image_" + time.Now().Format("20060102_150405") + ".jpg",
			img.GetURL(), img.GetMediaKey(), img.GetFileSHA256(), img.GetFileEncSHA256(), img.GetFileLength()
	}

	// Check for video message
	if vid := msg.GetVideoMessage(); vid != nil {
		return "video", "video_" + time.Now().Format("20060102_150405") + ".mp4",
			vid.GetURL(), vid.GetMediaKey(), vid.GetFileSHA256(), vid.GetFileEncSHA256(), vid.GetFileLength()
	}

	// Check for audio message
	if aud := msg.GetAudioMessage(); aud != nil {
		return "audio", "audio_" + time.Now().Format("20060102_150405") + ".ogg",
			aud.GetURL(), aud.GetMediaKey(), aud.GetFileSHA256(), aud.GetFileEncSHA256(), aud.GetFileLength()
	}

	// Check for document message
	if doc := msg.GetDocumentMessage(); doc != nil {
		filename := doc.GetFileName()
		if filename == "" {
			filename = "document_" + time.Now().Format("20060102_150405")
		}
		return "document", filename,
			doc.GetURL(), doc.GetMediaKey(), doc.GetFileSHA256(), doc.GetFileEncSHA256(), doc.GetFileLength()
	}

	return "", "", "", nil, nil, nil, 0
}

// sendWebhook sends a message to Bijou's webhook endpoint
func sendWebhook(msg Message, webhookURL string, logger waLog.Logger) {
	// Add tenant info to payload
	payload, err := json.Marshal(msg)
	if err != nil {
		logger.Errorf("Failed to marshal webhook payload: %v", err)
		return
	}

	// Send POST request to webhook
	resp, err := http.Post(webhookURL, "application/json", bytes.NewBuffer(payload))
	if err != nil {
		logger.Errorf("Failed to send webhook to %s: %v", webhookURL, err)
		return
	}
	defer resp.Body.Close()

	// Check response
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		logger.Infof("✅ Webhook sent successfully for message %s (Tenant: %s)", msg.ID, msg.TenantID)
	} else {
		logger.Warnf("⚠️ Webhook returned status %d for message %s (Tenant: %s)", resp.StatusCode, msg.ID, msg.TenantID)
	}
}

// Handle regular incoming messages with media support
func handleMessage(client *whatsmeow.Client, messageStore *MessageStore, tenantID string, msg *events.Message, logger waLog.Logger) {
	// Save message to database
	chatJID := msg.Info.Chat.String()
	sender := msg.Info.Sender.User

	// Get appropriate chat name
	name := GetChatName(client, messageStore, tenantID, msg.Info.Chat, chatJID, nil, sender, logger)

	// Update chat in database
	err := messageStore.StoreChat(chatJID, tenantID, name, msg.Info.Timestamp)
	if err != nil {
		logger.Warnf("Failed to store chat: %v", err)
	}

	// Extract text content
	content := extractTextContent(msg.Message)

	// Extract media info
	mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength := extractMediaInfo(msg.Message)

	// Debug: Log message structure if extraction failed
	if content == "" && mediaType == "" {
		logger.Warnf("⚠️ EMPTY MESSAGE - ID: %s, Chat: %s, Sender: %s, Timestamp: %v, IsFromMe: %v, MessageType: %T",
			msg.Info.ID, chatJID, sender, msg.Info.Timestamp, msg.Info.IsFromMe, msg.Message)

		// Try to log what fields are present
		if msg.Message != nil {
			logger.Warnf("Message fields present: Conversation=%v, ExtendedText=%v, Image=%v, Video=%v, Document=%v, Audio=%v",
				msg.Message.Conversation != nil,
				msg.Message.ExtendedTextMessage != nil,
				msg.Message.ImageMessage != nil,
				msg.Message.VideoMessage != nil,
				msg.Message.DocumentMessage != nil,
				msg.Message.AudioMessage != nil)
		}
		return
	}

	// Store message in database
	err = messageStore.StoreMessage(
		msg.Info.ID,
		chatJID,
		tenantID,
		sender,
		content,
		msg.Info.Timestamp,
		msg.Info.IsFromMe,
		mediaType,
		filename,
		url,
		mediaKey,
		fileSHA256,
		fileEncSHA256,
		fileLength,
	)

	if err != nil {
		logger.Warnf("Failed to store message: %v", err)
	} else {
		// Log message reception AND successful storage
		timestamp := msg.Info.Timestamp.Format("2006-01-02 15:04:05")
		direction := "←"
		if msg.Info.IsFromMe {
			direction = "→"
		}

		// Log based on message type
		if mediaType != "" {
			fmt.Printf("[%s] %s %s: [%s: %s] %s\n", timestamp, direction, sender, mediaType, filename, content)
			logger.Infof("✅ STORED: [%s] %s -> %s: [%s: %s] %s", timestamp, sender, chatJID, mediaType, filename, content)
		} else if content != "" {
			fmt.Printf("[%s] %s %s: %s\n", timestamp, direction, sender, content)
			logger.Infof("✅ STORED: [%s] %s -> %s: %s", timestamp, sender, chatJID, content)
		}

		// Send webhook notification to Bijou
		if !msg.Info.IsFromMe {
			webhookURL := os.Getenv("BIJOU_WEBHOOK_URL")
			if webhookURL != "" {
				webhookMsg := Message{
					ID:          msg.Info.ID,
					ChatJID:     chatJID,
					TenantID:    tenantID,
					Sender:      sender,
					Content:     content,
					Time:        msg.Info.Timestamp,
					IsFromMe:    msg.Info.IsFromMe,
					MediaType:   mediaType,
					Filename:    filename,
					BusinessJID: client.Store.ID.String(),
				}
				sendWebhook(webhookMsg, webhookURL, logger)
			}
		}
	}
}

// DownloadMediaRequest represents the request body for the download media API
type DownloadMediaRequest struct {
	TenantID  string `json:"tenant_id"`
	MessageID string `json:"message_id"`
	ChatJID   string `json:"chat_jid"`
}

// DownloadMediaResponse represents the response for the download media API
type DownloadMediaResponse struct {
	Success  bool   `json:"success"`
	Message  string `json:"message"`
	Filename string `json:"filename,omitempty"`
	Path     string `json:"path,omitempty"`
}

// ListMessagesRequest represents the query parameters for listing messages
type ListMessagesRequest struct {
	ChatJID string `json:"chat_jid"`
	Limit   int    `json:"limit"`
	Since   string `json:"since"` // ISO timestamp
}

// ListMessagesResponse represents the response for the list messages API
type ListMessagesResponse struct {
	Success  bool      `json:"success"`
	Messages []Message `json:"messages"`
}

// Store additional media info in the database
func (store *MessageStore) StoreMediaInfo(id, chatJID, url string, mediaKey, fileSHA256, fileEncSHA256 []byte, fileLength uint64) error {
	_, err := store.db.Exec(
		"UPDATE messages SET url = ?, media_key = ?, file_sha256 = ?, file_enc_sha256 = ?, file_length = ? WHERE id = ? AND chat_jid = ?",
		url, mediaKey, fileSHA256, fileEncSHA256, fileLength, id, chatJID,
	)
	return err
}

// Get media info from the database
func (store *MessageStore) GetMediaInfo(id, chatJID string) (string, string, string, []byte, []byte, []byte, uint64, error) {
	var mediaType, filename, url string
	var mediaKey, fileSHA256, fileEncSHA256 []byte
	var fileLength uint64

	err := store.db.QueryRow(
		"SELECT media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length FROM messages WHERE id = ? AND chat_jid = ?",
		id, chatJID,
	).Scan(&mediaType, &filename, &url, &mediaKey, &fileSHA256, &fileEncSHA256, &fileLength)

	return mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength, err
}

// MediaDownloader implements the whatsmeow.DownloadableMessage interface
type MediaDownloader struct {
	URL           string
	DirectPath    string
	MediaKey      []byte
	FileLength    uint64
	FileSHA256    []byte
	FileEncSHA256 []byte
	MediaType     whatsmeow.MediaType
}

// GetDirectPath implements the DownloadableMessage interface
func (d *MediaDownloader) GetDirectPath() string {
	return d.DirectPath
}

// GetURL implements the DownloadableMessage interface
func (d *MediaDownloader) GetURL() string {
	return d.URL
}

// GetMediaKey implements the DownloadableMessage interface
func (d *MediaDownloader) GetMediaKey() []byte {
	return d.MediaKey
}

// GetFileLength implements the DownloadableMessage interface
func (d *MediaDownloader) GetFileLength() uint64 {
	return d.FileLength
}

// GetFileSHA256 implements the DownloadableMessage interface
func (d *MediaDownloader) GetFileSHA256() []byte {
	return d.FileSHA256
}

// GetFileEncSHA256 implements the DownloadableMessage interface
func (d *MediaDownloader) GetFileEncSHA256() []byte {
	return d.FileEncSHA256
}

// GetMediaType implements the DownloadableMessage interface
func (d *MediaDownloader) GetMediaType() whatsmeow.MediaType {
	return d.MediaType
}

// Function to download media from a message
func downloadMedia(client *whatsmeow.Client, messageStore *MessageStore, messageID, chatJID string) (bool, string, string, string, error) {
	// Query the database for the message
	var mediaType, filename, url string
	var mediaKey, fileSHA256, fileEncSHA256 []byte
	var fileLength uint64
	var err error

	// First, check if we already have this file
	chatDir := fmt.Sprintf("store/%s", strings.ReplaceAll(chatJID, ":", "_"))
	localPath := ""

	// Get media info from the database
	mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength, err = messageStore.GetMediaInfo(messageID, chatJID)

	if err != nil {
		// Try to get basic info if extended info isn't available
		err = messageStore.db.QueryRow(
			"SELECT media_type, filename FROM messages WHERE id = ? AND chat_jid = ?",
			messageID, chatJID,
		).Scan(&mediaType, &filename)

		if err != nil {
			return false, "", "", "", fmt.Errorf("failed to find message: %v", err)
		}
	}

	// Check if this is a media message
	if mediaType == "" {
		return false, "", "", "", fmt.Errorf("not a media message")
	}

	// Create directory for the chat if it doesn't exist
	if err := os.MkdirAll(chatDir, 0755); err != nil {
		return false, "", "", "", fmt.Errorf("failed to create chat directory: %v", err)
	}

	// Generate a local path for the file
	localPath = fmt.Sprintf("%s/%s", chatDir, filename)

	// Get absolute path
	absPath, err := filepath.Abs(localPath)
	if err != nil {
		return false, "", "", "", fmt.Errorf("failed to get absolute path: %v", err)
	}

	// Check if file already exists
	if _, err := os.Stat(localPath); err == nil {
		// File exists, return it
		return true, mediaType, filename, absPath, nil
	}

	// If we don't have all the media info we need, we can't download
	if url == "" || len(mediaKey) == 0 || len(fileSHA256) == 0 || len(fileEncSHA256) == 0 || fileLength == 0 {
		return false, "", "", "", fmt.Errorf("incomplete media information for download")
	}

	fmt.Printf("Attempting to download media for message %s in chat %s...\n", messageID, chatJID)

	// Extract direct path from URL
	directPath := extractDirectPathFromURL(url)

	// Create a downloader that implements DownloadableMessage
	var waMediaType whatsmeow.MediaType
	switch mediaType {
	case "image":
		waMediaType = whatsmeow.MediaImage
	case "video":
		waMediaType = whatsmeow.MediaVideo
	case "audio":
		waMediaType = whatsmeow.MediaAudio
	case "document":
		waMediaType = whatsmeow.MediaDocument
	default:
		return false, "", "", "", fmt.Errorf("unsupported media type: %s", mediaType)
	}

	downloader := &MediaDownloader{
		URL:           url,
		DirectPath:    directPath,
		MediaKey:      mediaKey,
		FileLength:    fileLength,
		FileSHA256:    fileSHA256,
		FileEncSHA256: fileEncSHA256,
		MediaType:     waMediaType,
	}

	// Download the media using whatsmeow client
	mediaData, err := client.Download(context.Background(), downloader)
	if err != nil {
		return false, "", "", "", fmt.Errorf("failed to download media: %v", err)
	}

	// Save the downloaded media to file
	if err := os.WriteFile(localPath, mediaData, 0644); err != nil {
		return false, "", "", "", fmt.Errorf("failed to save media file: %v", err)
	}

	fmt.Printf("Successfully downloaded %s media to %s (%d bytes)\n", mediaType, absPath, len(mediaData))
	return true, mediaType, filename, absPath, nil
}

// Extract direct path from a WhatsApp media URL
func extractDirectPathFromURL(url string) string {
	// The direct path is typically in the URL, we need to extract it
	// Example URL: https://mmg.whatsapp.net/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc?ccb=11-4&oh=...

	// Find the path part after the domain
	parts := strings.SplitN(url, ".net/", 2)
	if len(parts) < 2 {
		return url // Return original URL if parsing fails
	}

	pathPart := parts[1]

	// Remove query parameters
	pathPart = strings.SplitN(pathPart, "?", 2)[0]

	// Create proper direct path format
	return "/" + pathPart
}

// Start a REST API server to expose the WhatsApp client functionality
func startRESTServer(clients *sync.Map, messageStore *MessageStore, port int, qrChannels *sync.Map) {
	// Handler for getting the QR code image
	http.HandleFunc("/qr", func(w http.ResponseWriter, r *http.Request) {
		tenantID := r.URL.Query().Get("tenant_id")
		if tenantID == "" {
			http.Error(w, "tenant_id index is required", http.StatusBadRequest)
			return
		}

		// Check if we already have a client (and if it's connected)
		if val, ok := clients.Load(tenantID); ok {
			client := val.(*whatsmeow.Client)
			if client.IsConnected() && client.Store.ID != nil {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(map[string]interface{}{
					"success": true,
					"status":  "connected",
					"message": "Already connected",
				})
				return
			}
		}

		// Look for a pending QR in the map
		var png []byte
		if val, ok := qrChannels.Load(tenantID); ok {
			png = val.([]byte)
		}

		if png == nil {
			http.Error(w, "QR code not available for this tenant. Try initializing first.", http.StatusNotFound)
			return
		}

		w.Header().Set("Content-Type", "image/png")
		w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		w.Write(png)
	})

	// Handler for sending messages
	http.HandleFunc("/api/send", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req SendMessageRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		if req.TenantID == "" {
			http.Error(w, "tenant_id is required", http.StatusBadRequest)
			return
		}

		val, ok := clients.Load(req.TenantID)
		if !ok {
			http.Error(w, "No active WhatsApp session for this tenant", http.StatusNotFound)
			return
		}
		client := val.(*whatsmeow.Client)

		success, message := sendWhatsAppMessage(client, req.Recipient, req.Message, req.MediaPath)

		w.Header().Set("Content-Type", "application/json")
		if !success {
			w.WriteHeader(http.StatusInternalServerError)
		}
		json.NewEncoder(w).Encode(SendMessageResponse{
			Success: success,
			Message: message,
		})
	})

	// Backward-compatible alias for older clients
	http.HandleFunc("/send", func(w http.ResponseWriter, r *http.Request) {
		r.URL.Path = "/api/send"
		http.DefaultServeMux.ServeHTTP(w, r)
	})

	// Handler for health check
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		connectedCount := 0
		clients.Range(func(key, value interface{}) bool {
			client := value.(*whatsmeow.Client)
			if client.IsConnected() {
				connectedCount++
			}
			return true
		})

		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":          "running",
			"uptime":          time.Since(startTime).String(),
			"active_sessions": connectedCount,
		})
	})

	// Handler for listing messages
	http.HandleFunc("/api/messages", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		tenantID := r.URL.Query().Get("tenant_id")
		if tenantID == "" {
			http.Error(w, "tenant_id is required", http.StatusBadRequest)
			return
		}

		since := r.URL.Query().Get("since")
		limitStr := r.URL.Query().Get("limit")
		chatJID := r.URL.Query().Get("chat_jid")

		limit := 50
		if limitStr != "" {
			fmt.Sscanf(limitStr, "%d", &limit)
		}

		query := "SELECT id, chat_jid, tenant_id, sender, content, timestamp, is_from_me, media_type, filename FROM messages WHERE tenant_id = ?"
		args := []interface{}{tenantID}

		if since != "" {
			sinceTime, err := time.Parse(time.RFC3339, since)
			if err == nil {
				query += " AND timestamp > ?"
				args = append(args, sinceTime.Format("2006-01-02 15:04:05"))
			}
		}

		if chatJID != "" {
			query += " AND chat_jid = ?"
			args = append(args, chatJID)
		}

		query += " ORDER BY timestamp ASC LIMIT ?"
		args = append(args, limit)

		rows, err := messageStore.db.Query(query, args...)
		if err != nil {
			http.Error(w, fmt.Sprintf("Database error: %v", err), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var messages []Message
		for rows.Next() {
			var msg Message
			var ts time.Time
			err := rows.Scan(&msg.ID, &msg.ChatJID, &msg.TenantID, &msg.Sender, &msg.Content, &ts, &msg.IsFromMe, &msg.MediaType, &msg.Filename)
			if err != nil {
				continue
			}
			msg.Time = ts
			messages = append(messages, msg)
		}

		json.NewEncoder(w).Encode(ListMessagesResponse{
			Success:  true,
			Messages: messages,
		})
	})

	// Handler for initializing a new session
	http.HandleFunc("/api/init", func(w http.ResponseWriter, r *http.Request) {
		tenantID := r.URL.Query().Get("tenant_id")
		if tenantID == "" {
			http.Error(w, "tenant_id index is required", http.StatusBadRequest)
			return
		}

		// Check if already active
		if _, ok := clients.Load(tenantID); ok {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"message": "Session already initialized or active",
			})
			return
		}

		// Start new client in background
		// We'll need a reference to the container and other globals
		// For now, assume a helper function StartClientForTenant exists
		go StartClientForTenant(tenantID, clients, qrChannels, messageStore)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Initialization started",
		})
	})

	// Start the server
	serverAddr := fmt.Sprintf(":%d", port)
	fmt.Printf("Starting Multi-Tenant REST API server on %s...\n", serverAddr)

	go func() {
		if err := http.ListenAndServe(serverAddr, nil); err != nil {
			fmt.Printf("REST API server error: %v\n", err)
		}
	}()
}

var startTime = time.Now()

var (
	container *sqlstore.Container
	waLogger  waLog.Logger
)

func main() {
	// Set up logger
	waLogger = waLog.Stdout("Client", "INFO", true)
	waLogger.Infof("Starting Multi-Tenant WhatsApp bridge...")

	port := 8080
	if portEnv := os.Getenv("PORT"); portEnv != "" {
		fmt.Sscanf(portEnv, "%d", &port)
	}

	// Maps to hold active clients and pending QRs
	var activeClients sync.Map
	var qrChannels sync.Map

	// Initialize message store
	ms, err := NewMessageStore()
	if err != nil {
		waLogger.Errorf("Failed to initialize message store: %v", err)
		return
	}
	defer ms.Close()

	// Initialize whatsmeow container
	dbLog := waLog.Stdout("Database", "INFO", true)
	if err := os.MkdirAll("store", 0755); err != nil {
		waLogger.Errorf("Failed to create store directory: %v", err)
		return
	}

	// Check for PostgreSQL connection string
	dbURL := os.Getenv("WHATSAPP_DB_URL")
	dbDriver := "sqlite"
	dbConnString := "file:store/whatsapp.db?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)"

	waLogger.Infof("🔍 Checking database configuration...")
	if dbURL != "" {
		waLogger.Infof("📊 WHATSAPP_DB_URL found: %s", dbURL[:20]+"...")
		// PostgreSQL connection provided
		if strings.Contains(dbURL, "postgres://") || strings.Contains(dbURL, "postgresql://") {
			dbDriver = "postgres"
			dbConnString = dbURL
			waLogger.Infof("✅ Using PostgreSQL for session storage")
		} else {
			waLogger.Warnf("⚠️ WHATSAPP_DB_URL set but not a PostgreSQL URL, falling back to SQLite")
			waLogger.Infof("📁 Using SQLite for session storage (file:store/whatsapp.db)")
		}
	} else {
		// Fallback to SQLite
		waLogger.Infof("📁 Using SQLite for session storage (file:store/whatsapp.db)")
	}

	container, err = sqlstore.New(context.Background(), dbDriver, dbConnString, dbLog)
	if err != nil {
		waLogger.Errorf("Failed to connect to whatsmeow database: %v", err)
		return
	}

	// Start REST API server
	startRESTServer(&activeClients, ms, port, &qrChannels)

	// Load existing sessions from database
	rows, err := ms.db.Query("SELECT tenant_id FROM sessions")
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var tenantID string
			if err := rows.Scan(&tenantID); err == nil {
				waLogger.Infof("Reloading session for tenant: %s", tenantID)
				go StartClientForTenant(tenantID, &activeClients, &qrChannels, ms)
			}
		}
	}

	// Keep alive
	exitChan := make(chan os.Signal, 1)
	signal.Notify(exitChan, syscall.SIGINT, syscall.SIGTERM)
	<-exitChan

	waLogger.Infof("Shutting down...")
	activeClients.Range(func(key, value interface{}) bool {
		client := value.(*whatsmeow.Client)
		client.Disconnect()
		return true
	})
}

// notifySupabaseConnection updates Supabase when WhatsApp successfully connects
func notifySupabaseConnection(tenantID string, whatsappJID string) {
	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	
	if supabaseURL == "" || supabaseKey == "" {
		waLogger.Warnf("[%s] Supabase credentials not configured, skipping notification", tenantID)
		return
	}
	
	// Prepare update payload
	now := time.Now().UTC().Format(time.RFC3339)
	updateData := map[string]interface{}{
		"whatsapp_jid":          whatsappJID,
		"whatsapp_connected_at": now,
		"onboarding_completed":  true,
		"status":                "active",
		"updated_at":            now,
	}
	
	jsonData, err := json.Marshal(updateData)
	if err != nil {
		waLogger.Errorf("[%s] Failed to marshal Supabase update: %v", tenantID, err)
		return
	}
	
	// Make PATCH request to Supabase
	url := fmt.Sprintf("%s/rest/v1/tenants?id=eq.%s", supabaseURL, tenantID)
	req, err := http.NewRequest("PATCH", url, bytes.NewBuffer(jsonData))
	if err != nil {
		waLogger.Errorf("[%s] Failed to create Supabase request: %v", tenantID, err)
		return
	}
	
	req.Header.Set("apikey", supabaseKey)
	req.Header.Set("Authorization", "Bearer "+supabaseKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Prefer", "return=representation")
	
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		waLogger.Errorf("[%s] Failed to notify Supabase: %v", tenantID, err)
		return
	}
	defer resp.Body.Close()
	
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		waLogger.Infof("[%s] ✅ Notified Supabase of WhatsApp connection: %s", tenantID, whatsappJID)
	} else {
		body := make([]byte, 500)
		resp.Body.Read(body)
		waLogger.Errorf("[%s] Supabase update failed with status %d: %s", tenantID, resp.StatusCode, string(body))
	}
}

// StartClientForTenant handles the lifecycle of a single tenant's WhatsApp client
func StartClientForTenant(tenantID string, clients *sync.Map, qrChannels *sync.Map, messageStore *MessageStore) {
	// 1. Get Device Store
	var deviceStore *store.Device

	// Try to find JID for this tenant
	var jidStr string
	err := messageStore.db.QueryRow("SELECT jid FROM sessions WHERE tenant_id = ?", tenantID).Scan(&jidStr)

	if err == nil && jidStr != "" {
		jid, _ := types.ParseJID(jidStr)
		deviceStore, err = container.GetDevice(context.Background(), jid)
	}

	if deviceStore == nil {
		waLogger.Infof("[%s] No existing session, creating new device", tenantID)
		deviceStore = container.NewDevice()
	}

	// 2. Create Client
	client := whatsmeow.NewClient(deviceStore, waLog.Stdout(fmt.Sprintf("Client-%s", tenantID), "INFO", true))
	clients.Store(tenantID, client)

	// 3. Add Event Handler
	client.AddEventHandler(func(evt interface{}) {
		switch v := evt.(type) {
		case *events.Message:
			handleMessage(client, messageStore, tenantID, v, waLogger)
		case *events.HistorySync:
			enableHistorySync := os.Getenv("ENABLE_HISTORY_SYNC")
			if enableHistorySync == "true" {
				handleHistorySync(client, messageStore, tenantID, v, waLogger)
			}
		case *events.Connected:
			waLogger.Infof("[%s] Connected", tenantID)
			// Store JID in sessions table if we have one now
			if client.Store.ID != nil {
				messageStore.db.Exec("INSERT OR REPLACE INTO sessions (tenant_id, jid) VALUES (?, ?)",
					tenantID, client.Store.ID.String())
			}
		}
	})

	// 4. Connect / QR Flow
	if client.Store.ID == nil {
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			waLogger.Errorf("[%s] Failed to connect: %v", tenantID, err)
			return
		}

		for evt := range qrChan {
			if evt.Event == "code" {
				waLogger.Infof("[%s] New QR code generated", tenantID)
				code, err := qr.Encode(evt.Code, qr.L)
				if err == nil {
					qrChannels.Store(tenantID, code.PNG())
				}
		} else if evt.Event == "success" {
			waLogger.Infof("[%s] Successfully authenticated!", tenantID)
			qrChannels.Delete(tenantID)
			// Re-save session with JID
			if client.Store.ID != nil {
				messageStore.db.Exec("INSERT OR REPLACE INTO sessions (tenant_id, jid) VALUES (?, ?)",
					tenantID, client.Store.ID.String())
				
				// Notify Supabase that WhatsApp is connected
				go notifySupabaseConnection(tenantID, client.Store.ID.String())
			}
			break
		}
		}
	} else {
		err = client.Connect()
		if err != nil {
			waLogger.Errorf("[%s] Failed to connect: %v", tenantID, err)
			return
		}
	}
}

// GetChatName determines the appropriate name for a chat based on JID and other info
func GetChatName(client *whatsmeow.Client, messageStore *MessageStore, tenantID string, jid types.JID, chatJID string, conversation interface{}, sender string, logger waLog.Logger) string {
	// First, check if chat already exists in database with a name
	var existingName string
	err := messageStore.db.QueryRow("SELECT name FROM chats WHERE jid = ? AND tenant_id = ?", chatJID, tenantID).Scan(&existingName)
	if err == nil && existingName != "" {
		// Chat exists with a name, use that
		logger.Infof("Using existing chat name for %s (Tenant: %s): %s", chatJID, tenantID, existingName)
		return existingName
	}

	// Need to determine chat name
	var name string

	if jid.Server == "g.us" {
		// This is a group chat
		logger.Infof("Getting name for group: %s", chatJID)

		// Use conversation data if provided (from history sync)
		if conversation != nil {
			// Extract name from conversation if available
			// This uses type assertions to handle different possible types
			var displayName, convName *string
			// Try to extract the fields we care about regardless of the exact type
			v := reflect.ValueOf(conversation)
			if v.Kind() == reflect.Ptr && !v.IsNil() {
				v = v.Elem()

				// Try to find DisplayName field
				if displayNameField := v.FieldByName("DisplayName"); displayNameField.IsValid() && displayNameField.Kind() == reflect.Ptr && !displayNameField.IsNil() {
					dn := displayNameField.Elem().String()
					displayName = &dn
				}

				// Try to find Name field
				if nameField := v.FieldByName("Name"); nameField.IsValid() && nameField.Kind() == reflect.Ptr && !nameField.IsNil() {
					n := nameField.Elem().String()
					convName = &n
				}
			}

			// Use the name we found
			if displayName != nil && *displayName != "" {
				name = *displayName
			} else if convName != nil && *convName != "" {
				name = *convName
			}
		}

		// If we didn't get a name, try group info
		if name == "" {
			groupInfo, err := client.GetGroupInfo(context.Background(), jid)
			if err == nil && groupInfo.Name != "" {
				name = groupInfo.Name
			} else {
				// Fallback name for groups
				name = fmt.Sprintf("Group %s", jid.User)
			}
		}

		logger.Infof("Using group name: %s", name)
	} else {
		// This is an individual contact
		logger.Infof("Getting name for contact: %s", chatJID)

		// Just use contact info (full name)
		contact, err := client.Store.Contacts.GetContact(context.Background(), jid)
		if err == nil && contact.FullName != "" {
			name = contact.FullName
		} else if sender != "" {
			// Fallback to sender
			name = sender
		} else {
			// Last fallback to JID
			name = jid.User
		}

		logger.Infof("Using contact name: %s", name)
	}

	return name
}

// Handle history sync events
func handleHistorySync(client *whatsmeow.Client, messageStore *MessageStore, tenantID string, historySync *events.HistorySync, logger waLog.Logger) {
	fmt.Printf("Received history sync event for Tenant %s with %d conversations\n", tenantID, len(historySync.Data.Conversations))

	syncedCount := 0
	for _, conversation := range historySync.Data.Conversations {
		// ... existing loop logic ...
		if conversation.ID == nil {
			continue
		}

		chatJID := *conversation.ID

		jid, err := types.ParseJID(chatJID)
		if err != nil {
			logger.Warnf("Failed to parse JID %s: %v", chatJID, err)
			continue
		}

		name := GetChatName(client, messageStore, tenantID, jid, chatJID, conversation, "", logger)

		// Process messages
		messages := conversation.Messages
		if len(messages) > 0 {
			latestMsg := messages[0]
			if latestMsg == nil || latestMsg.Message == nil {
				continue
			}

			timestamp := time.Time{}
			if ts := latestMsg.Message.GetMessageTimestamp(); ts != 0 {
				timestamp = time.Unix(int64(ts), 0)
			} else {
				continue
			}

			messageStore.StoreChat(chatJID, tenantID, name, timestamp)

			// Store messages
			for _, msg := range messages {
				if msg == nil || msg.Message == nil {
					continue
				}

				// Extract text content
				var content string
				if msg.Message.Message != nil {
					if conv := msg.Message.Message.GetConversation(); conv != "" {
						content = conv
					} else if ext := msg.Message.Message.GetExtendedTextMessage(); ext != nil {
						content = ext.GetText()
					}
				}

				// Extract media info
				var mediaType, filename, url string
				var mediaKey, fileSHA256, fileEncSHA256 []byte
				var fileLength uint64

				if msg.Message.Message != nil {
					mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength = extractMediaInfo(msg.Message.Message)
				}

				// Log the message content for debugging
				logger.Infof("Message content: %v, Media Type: %v", content, mediaType)

				// Skip messages with no content and no media
				if content == "" && mediaType == "" {
					continue
				}

				// Determine sender
				var sender string
				isFromMe := false
				if msg.Message.Key != nil {
					if msg.Message.Key.FromMe != nil {
						isFromMe = *msg.Message.Key.FromMe
					}
					if !isFromMe && msg.Message.Key.Participant != nil && *msg.Message.Key.Participant != "" {
						sender = *msg.Message.Key.Participant
					} else if isFromMe {
						sender = client.Store.ID.User
					} else {
						sender = jid.User
					}
				} else {
					sender = jid.User
				}

				// Store message
				msgID := ""
				if msg.Message.Key != nil && msg.Message.Key.ID != nil {
					msgID = *msg.Message.Key.ID
				}

				// Get message timestamp
				timestamp := time.Time{}
				if ts := msg.Message.GetMessageTimestamp(); ts != 0 {
					timestamp = time.Unix(int64(ts), 0)
				} else {
					continue
				}

				err = messageStore.StoreMessage(
					msgID,
					chatJID,
					tenantID,
					sender,
					content,
					timestamp,
					isFromMe,
					mediaType,
					filename,
					url,
					mediaKey,
					fileSHA256,
					fileEncSHA256,
					fileLength,
				)
				if err != nil {
					logger.Warnf("Failed to store history message: %v", err)
				} else {
					syncedCount++
					// Log successful message storage
					if mediaType != "" {
						logger.Infof("Stored message: [%s] %s -> %s: [%s: %s] %s",
							timestamp.Format("2006-01-02 15:04:05"), sender, chatJID, mediaType, filename, content)
					} else {
						logger.Infof("Stored message: [%s] %s -> %s: %s",
							timestamp.Format("2006-01-02 15:04:05"), sender, chatJID, content)
					}
				}
			}
		}
	}

	fmt.Printf("History sync complete. Stored %d messages.\n", syncedCount)
}

// Request history sync from the server
func requestHistorySync(client *whatsmeow.Client) {
	if client == nil {
		fmt.Println("Client is not initialized. Cannot request history sync.")
		return
	}

	if !client.IsConnected() {
		fmt.Println("Client is not connected. Please ensure you are connected to WhatsApp first.")
		return
	}

	if client.Store.ID == nil {
		fmt.Println("Client is not logged in. Please scan the QR code first.")
		return
	}

	// Build and send a history sync request
	historyMsg := client.BuildHistorySyncRequest(nil, 100)
	if historyMsg == nil {
		fmt.Println("Failed to build history sync request.")
		return
	}

	_, err := client.SendMessage(context.Background(), types.JID{
		Server: "s.whatsapp.net",
		User:   "status",
	}, historyMsg)

	if err != nil {
		fmt.Printf("Failed to request history sync: %v\n", err)
	} else {
		fmt.Println("History sync requested. Waiting for server response...")
	}
}

// analyzeOggOpus tries to extract duration and generate a simple waveform from an Ogg Opus file
func analyzeOggOpus(data []byte) (duration uint32, waveform []byte, err error) {
	// Try to detect if this is a valid Ogg file by checking for the "OggS" signature
	// at the beginning of the file
	if len(data) < 4 || string(data[0:4]) != "OggS" {
		return 0, nil, fmt.Errorf("not a valid Ogg file (missing OggS signature)")
	}

	// Parse Ogg pages to find the last page with a valid granule position
	var lastGranule uint64
	var sampleRate uint32 = 48000 // Default Opus sample rate
	var preSkip uint16 = 0
	var foundOpusHead bool

	// Scan through the file looking for Ogg pages
	for i := 0; i < len(data); {
		// Check if we have enough data to read Ogg page header
		if i+27 >= len(data) {
			break
		}

		// Verify Ogg page signature
		if string(data[i:i+4]) != "OggS" {
			// Skip until next potential page
			i++
			continue
		}

		// Extract header fields
		granulePos := binary.LittleEndian.Uint64(data[i+6 : i+14])
		pageSeqNum := binary.LittleEndian.Uint32(data[i+18 : i+22])
		numSegments := int(data[i+26])

		// Extract segment table
		if i+27+numSegments >= len(data) {
			break
		}
		segmentTable := data[i+27 : i+27+numSegments]

		// Calculate page size
		pageSize := 27 + numSegments
		for _, segLen := range segmentTable {
			pageSize += int(segLen)
		}

		// Check if we're looking at an OpusHead packet (should be in first few pages)
		if !foundOpusHead && pageSeqNum <= 1 {
			// Look for "OpusHead" marker in this page
			pageData := data[i : i+pageSize]
			headPos := bytes.Index(pageData, []byte("OpusHead"))
			if headPos >= 0 && headPos+12 < len(pageData) {
				// Found OpusHead, extract sample rate and pre-skip
				// OpusHead format: Magic(8) + Version(1) + Channels(1) + PreSkip(2) + SampleRate(4) + ...
				headPos += 8 // Skip "OpusHead" marker
				// PreSkip is 2 bytes at offset 10
				if headPos+12 <= len(pageData) {
					preSkip = binary.LittleEndian.Uint16(pageData[headPos+10 : headPos+12])
					sampleRate = binary.LittleEndian.Uint32(pageData[headPos+12 : headPos+16])
					foundOpusHead = true
					fmt.Printf("Found OpusHead: sampleRate=%d, preSkip=%d\n", sampleRate, preSkip)
				}
			}
		}

		// Keep track of last valid granule position
		if granulePos != 0 {
			lastGranule = granulePos
		}

		// Move to next page
		i += pageSize
	}

	if !foundOpusHead {
		fmt.Println("Warning: OpusHead not found, using default values")
	}

	// Calculate duration based on granule position
	if lastGranule > 0 {
		// Formula for duration: (lastGranule - preSkip) / sampleRate
		durationSeconds := float64(lastGranule-uint64(preSkip)) / float64(sampleRate)
		duration = uint32(math.Ceil(durationSeconds))
		fmt.Printf("Calculated Opus duration from granule: %f seconds (lastGranule=%d)\n",
			durationSeconds, lastGranule)
	} else {
		// Fallback to rough estimation if granule position not found
		fmt.Println("Warning: No valid granule position found, using estimation")
		durationEstimate := float64(len(data)) / 2000.0 // Very rough approximation
		duration = uint32(durationEstimate)
	}

	// Make sure we have a reasonable duration (at least 1 second, at most 300 seconds)
	if duration < 1 {
		duration = 1
	} else if duration > 300 {
		duration = 300
	}

	// Generate waveform
	waveform = placeholderWaveform(duration)

	fmt.Printf("Ogg Opus analysis: size=%d bytes, calculated duration=%d sec, waveform=%d bytes\n",
		len(data), duration, len(waveform))

	return duration, waveform, nil
}

// min returns the smaller of x or y
func min(x, y int) int {
	if x < y {
		return x
	}
	return y
}

// placeholderWaveform generates a synthetic waveform for WhatsApp voice messages
// that appears natural with some variability based on the duration
func placeholderWaveform(duration uint32) []byte {
	// WhatsApp expects a 64-byte waveform for voice messages
	const waveformLength = 64
	waveform := make([]byte, waveformLength)

	// Seed the random number generator for consistent results with the same duration
	rand.Seed(int64(duration))

	// Create a more natural looking waveform with some patterns and variability
	// rather than completely random values

	// Base amplitude and frequency - longer messages get faster frequency
	baseAmplitude := 35.0
	frequencyFactor := float64(min(int(duration), 120)) / 30.0

	for i := range waveform {
		// Position in the waveform (normalized 0-1)
		pos := float64(i) / float64(waveformLength)

		// Create a wave pattern with some randomness
		// Use multiple sine waves of different frequencies for more natural look
		val := baseAmplitude * math.Sin(pos*math.Pi*frequencyFactor*8)
		val += (baseAmplitude / 2) * math.Sin(pos*math.Pi*frequencyFactor*16)

		// Add some randomness to make it look more natural
		val += (rand.Float64() - 0.5) * 15

		// Add some fade-in and fade-out effects
		fadeInOut := math.Sin(pos * math.Pi)
		val = val * (0.7 + 0.3*fadeInOut)

		// Center around 50 (typical voice baseline)
		val = val + 50

		// Ensure values stay within WhatsApp's expected range (0-100)
		if val < 0 {
			val = 0
		} else if val > 100 {
			val = 100
		}

		waveform[i] = byte(val)
	}

	return waveform
}
