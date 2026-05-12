import pika
import json
import requests
from app.core.config import settings

def process_notification(ch, method, properties, body):
    data = json.loads(body)
    event_type = data.get("event")
    
    if event_type == "PRODUCT_DELETED":
        message = (
            f"🗑️ **Product Deleted**\n"
            f"**Store ID:** {data['tenant_id']}\n"
            f"**Item:** {data['product_name']} ({data['sku']})\n"
            f"**Actor ID:** {data['deleted_by']}"
        )
        
        # Send to Discord Webhook
        requests.post(settings.DISCORD_WEBHOOK_URL, json={"content": message})
        print(f" [x] Discord notification sent for {data['sku']}")

def start_worker():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='nexcore_notifications')

    print(' [*] Pelipper Post Office is open. Waiting for messages...')
    channel.basic_consume(
        queue='nexcore_notifications', 
        on_message_callback=process_notification, 
        auto_ack=True
    )
    channel.start_consuming()

if __name__ == '__main__':
    start_worker()