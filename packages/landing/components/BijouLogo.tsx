/**
 * Bijou AI — Signal Gem logo component.  © W3J LLC.
 *
 * Pure inline SVG. No network request, no font dependency, no raster.
 * Matches the official signal-gem-system master geometry — do not hand-edit
 * the path data. Pair with the SVG/PNG assets in /public/logos/ for cases
 * where a static file is required (favicons, OG image).
 *
 * Source: w3j-media-pack/.../signal-gem-system/bijoui-mark.svg
 * Brand sheet: w3j-media-pack/.../redesign-concepts/signal-gem-brand-board.html
 */
import * as React from "react";

/**
 * Brand palette — the official Signal Gem tokens. Keep in lock-step with
 * the CSS variables in index.html (--bj-green / --bj-gold / --bj-cream) and
 * with the tailwind config block in index.html.
 */
export const BIJOU = {
  green: "#0B3B2E", // Deep Bijou Green — primary brand color
  greenDeep: "#072A1F", // Deepest jewel tone — backgrounds
  gold: "#E3B457", // Bijou Gold — primary mark color
  goldDeep: "#D4A24C", // Aged gold — secondary
  goldSoft: "#B8860B", // Burnished gold — typography accents
  cream: "#F7F4EC", // Cream — body text on dark
  ink: "#0A0A0A", // Black — text on light backgrounds
} as const;

/**
 * Master path data (100-unit viewBox).
 *  - BODY: silhouette of the gem including the chat-bubble tail.
 *  - FACETS: inner cut lines (table, crown, girdle, pavilion) plus the
 *    chat-bubble tail facet. Drawn with stroke="currentColor" so the
 *    consumer can paint them via CSS.
 *  - BUBBLE: just the chat-bubble tail, used when an even simpler mark is
 *    needed (16px favicons, etc.).
 */
const BODY =
  "M30,12 L70,12 L88,40 L70,73 L50,73 L26,92 L33,73 L12,40 Z";
const FACETS = (
  <g
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    strokeLinejoin="round"
    strokeLinecap="round"
    opacity={0.55}
  >
    {/* Table (top center flat) */}
    <path d="M40,26 L60,26 L68,40 L60,54 L40,54 L32,40 Z" />
    {/* Vertical facet line through table */}
    <path d="M50,26 L50,54" />
    {/* Crown facets (top edges) */}
    <path d="M40,26 L30,12 M60,26 L70,12" />
    {/* Girdle lines (horizontal middle) */}
    <path d="M32,40 L12,40 M68,40 L88,40" />
    {/* Pavilion facets (bottom edges) */}
    <path d="M40,54 L30,73 M60,54 L70,73" />
    {/* Pavilion line through center */}
    <path d="M50,54 L50,73" />
    {/* Chat-bubble tail facet */}
    <path d="M50,73 L26,92 L33,73" />
  </g>
);

export type BijouTone = "gold" | "emerald" | "cream" | "white" | "black";
export type BijouSize = "sm" | "md" | "lg" | "xl";

const TONE_FILL: Record<BijouTone, string> = {
  gold: BIJOU.gold,
  emerald: BIJOU.green,
  cream: BIJOU.cream,
  white: "#FFFFFF",
  black: BIJOU.ink,
};

const SIZE_PX: Record<BijouSize, number> = {
  sm: 24,
  md: 40,
  lg: 96,
  xl: 200,
};

export interface BijouLogoProps extends Omit<React.SVGProps<SVGSVGElement>, "ref"> {
  /** rendered height in px. Defaults to 40 (md). */
  size?: number | BijouSize;
  /** Primary mark color. Default `gold`. */
  tone?: BijouTone;
  /** Show the inner facet lines. Disable for tiny sizes (<24px). */
  showFacets?: boolean;
  /** Force the simpler silhouette (no inner facets) regardless of size. */
  solid?: boolean;
  /** Accessible title. */
  title?: string;
}

/**
 * The Signal Gem mark. By default renders the full master geometry
 * (body + inner facet lines) in gold. Below 24px the facet lines
 * disappear automatically unless `solid` is true.
 */
export const BijouLogo: React.FC<BijouLogoProps> = ({
  size = "md",
  tone = "gold",
  showFacets,
  solid,
  title = "Bijou AI",
  ...rest
}) => {
  const px = typeof size === "number" ? size : SIZE_PX[size];
  const autoSolid = solid ?? px < 24;
  const withFacets = showFacets ?? !autoSolid;
  const fill = TONE_FILL[tone];

  return (
    <svg
      viewBox="0 0 100 100"
      role="img"
      aria-label={title}
      width={px}
      height={px}
      {...rest}
    >
      <title>{title}</title>
      <path
        d={BODY}
        fill={fill}
        fillRule="evenodd"
        style={{ color: fill }}
      />
      {withFacets && FACETS}
    </svg>
  );
};

/**
 * Horizontal lockup — gem on the left, "Bijou" wordmark on the right.
 * Matches /public/logos/lockup.svg exactly. Use when the wordmark is
 * needed inline (e.g. the auth screens, footer attribution).
 */
export interface BijouLockupProps extends Omit<React.SVGProps<SVGSVGElement>, "ref"> {
  size?: number;
  tone?: BijouTone;
  title?: string;
}

export const BijouLockup: React.FC<BijouLockupProps> = ({
  size = 40,
  tone = "gold",
  title = "Bijou AI",
  ...rest
}) => {
  const fill = TONE_FILL[tone];
  const markSize = size;
  const wordmarkWidth = size * 2.2;
  const totalWidth = markSize + 12 + wordmarkWidth;
  const gemScale = markSize / 100;

  return (
    <svg
      viewBox={`0 0 ${totalWidth} ${markSize}`}
      role="img"
      aria-label={title}
      width={totalWidth}
      height={markSize}
      {...rest}
    >
      <title>{title}</title>
      {/* Gem */}
      <g transform={`scale(${gemScale})`}>
        <path d={BODY} fill={fill} fillRule="evenodd" />
      </g>
      {/* Wordmark — uses serif "Bijou" + small-caps "AI" */}
      <g transform={`translate(${markSize + 12}, ${markSize * 0.78})`}>
        <text
          x={0}
          y={0}
          fontFamily='Optima, "Palatino Linotype", Georgia, serif'
          fontSize={markSize * 0.62}
          fill={fill}
          letterSpacing="0.5"
        >
          Bijou
        </text>
        <text
          x={markSize * 1.7}
          y={-markSize * 0.05}
          fontFamily="ui-sans-serif, system-ui, sans-serif"
          fontSize={markSize * 0.26}
          fill={fill}
          letterSpacing="3"
          fontWeight={600}
          opacity={0.7}
        >
          AI
        </text>
      </g>
    </svg>
  );
};

export default BijouLogo;
