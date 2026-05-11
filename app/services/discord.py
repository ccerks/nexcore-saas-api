import urllib.request
import json
from app.core.config import settings

class DiscordService:
    
    @staticmethod
    def send_alert(message: str) -> None:
        """
        Transmits critical system alerts to a secure Discord channel via Webhook.
        Fails silently to prevent blocking the main execution thread.
        """
        if not settings.DISCORD_WEBHOOK_URL:
            return
        
        payload = {
            "content": f"🚨 **NEXCORE SYSTEM ALERT** 🚨\n```\n{message}\n```"
        }
        
        req = urllib.request.Request(
            settings.DISCORD_WEBHOOK_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={
                'User-Agent': 'NexCore-Bot/1.0', 
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            print(f"⚠️ [DISCORD ALERT FAILED] Could not transmit webhook: {e}")