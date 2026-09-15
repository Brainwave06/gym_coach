import asyncio
import websockets
import base64
import cv2
import json

async def test_stream():
    uri = "ws://localhost:8000/stream/squat"
    
    # Create a dummy blank image for testing
    img = __import__("numpy").zeros((480, 640, 3), dtype=__import__("numpy").uint8)
        
    _, buffer = cv2.imencode('.jpg', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Send a dummy frame
        await websocket.send(img_base64)
        print("Sent frame")
        
        # Receive response
        response = await websocket.recv()
        print("Received:", json.loads(response))

if __name__ == "__main__":
    asyncio.run(test_stream())
