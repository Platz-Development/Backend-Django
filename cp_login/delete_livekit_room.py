import asyncio
from livekit.api import LiveKitAPI
from livekit.api import DeleteRoomRequest,ListRoomsRequest

LIVEKIT_API_KEY = "APIgaGhNfsBshoX"  
LIVEKIT_API_SECRET = "AHDvf9YF8rDob8v6fJ23D5UAefZT62xR5phWSFPZKgyC" 
LIVEKIT_WEBHOOK_SECRET = "your_webhook_secret" 
LIVEKIT_URL = "https://campusplatz-ckqf7pkr.livekit.cloud"


async def list_and_delete_room():
    try:
        async with LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ) as lkapi:
            # List all rooms
            rooms = await lkapi.room.list_rooms(ListRoomsRequest())
            if not rooms.rooms:
                print("ℹ️  No active rooms found.")
                return
            
            print("🧾 Active Rooms:")
            for i, room in enumerate(rooms.rooms, 1):
                print(f"{i}. {room.name}")

            # Prompt for room to delete
            room_to_delete = input("\nEnter the room name to delete (exactly as listed above): ").strip()
            if room_to_delete not in [r.name for r in rooms.rooms]:
                print(f"❌ Room '{room_to_delete}' does not exist in the current active list.")
                return

            # Delete the selected room
            await lkapi.room.delete_room(DeleteRoomRequest(room=room_to_delete))
            print(f"✅ Room '{room_to_delete}' deleted successfully.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_and_delete_room())