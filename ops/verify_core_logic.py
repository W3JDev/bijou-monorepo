import asyncio
import os
import sys

from dotenv import load_dotenv

# --- PATH SETUP ---
# Add the project root to sys.path so we can import 'w3j-bijou-enterprise'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "w3j-bijou-enterprise")
sys.path.append(src_path)

# Load env vars from project root
load_dotenv(os.path.join(project_root, ".env"))


async def main():
    print("🧪 STARTING SURGICAL VERIFICATION...")
    print(f"   Python Path included: {src_path}")

    # Import inside main to ensure paths are set
    try:
        from src.saas.tenant_router import TenantRouter
    except ImportError as e:
        print(f"   ❌ CRITICAL IMPORT ERROR: {e}")
        print(
            "      Make sure folder 'w3j-bijou-enterprise/src/saas' exists and has __init__.py"
        )
        return

    # 1. Test Tenant Router (Identity)
    print("\n[1] Testing Tenant Router (Identity Lookup)...")
    try:
        router = TenantRouter()
    except Exception as e:
        print(f"    ❌ CRITICAL: Could not initialize TenantRouter: {e}")
        print("       (Check your .env for SUPABASE_URL and SUPABASE_SERVICE_KEY)")
        return

    # Test WhatsApp Lookup
    wa_phone = "+601160600963"
    print(f"    Looking up WhatsApp: {wa_phone}")
    try:
        tenant_id_wa = await router.get_tenant_id_by_identifier(wa_phone)

        if tenant_id_wa == "06e152aa-8090-419f-be07-7cb1f9cc409d":
            print(f"    ✅ SUCCESS: Found Jewel via WhatsApp! ID: {tenant_id_wa}")
        else:
            print(f"    ❌ FAILED: Got {tenant_id_wa}, expected 06e152aa...")
            if not tenant_id_wa:
                print("       (Check if 'tenants' table has this phone number)")
    except Exception as e:
        print(f"    ❌ ERROR calling get_tenant_id_by_identifier: {e}")

    # Test Telegram Lookup
    tg_handle = "mebijou"
    print(f"    Looking up Telegram: {tg_handle}")
    try:
        tenant_id_tg = await router.get_tenant_id_by_identifier(tg_handle)

        if tenant_id_tg == "06e152aa-8090-419f-be07-7cb1f9cc409d":
            print(f"    ✅ SUCCESS: Found Jewel via Telegram! ID: {tenant_id_tg}")
        else:
            print(f"    ❌ FAILED: Got {tenant_id_tg}")
    except Exception as e:
        print(f"    ❌ ERROR calling get_tenant_id_by_identifier: {e}")

    # 2. Test Client Config (Vibe Check)
    print("\n[2] Testing Client Config Load...")
    # Use whichever ID we found
    target_id = locals().get("tenant_id_wa") or locals().get("tenant_id_tg")

    if target_id:
        try:
            config = await router.get_client_config(target_id)
            if config:
                print(
                    f"    Loaded Config for: {config.get('business_name', 'Unknown')}"
                )
                print(f"    Manglish Level: {config.get('manglish_level')}")

                if config.get("manglish_level") == "heavy":
                    print("    ✅ SUCCESS: Loaded 'Heavy Manglish' setting!")
                else:
                    print(
                        f"    ❌ FAILED: Manglish level is {config.get('manglish_level')}"
                    )
            else:
                print("    ❌ FAILED: Config is None")
        except Exception as e:
            print(f"    ❌ ERROR calling get_client_config: {e}")
    else:
        print("    ⚠️ SKIPPING Config Test (Tenant ID not found)")

    print("\n✨ VERIFICATION COMPLETE.")


if __name__ == "__main__":
    asyncio.run(main())
