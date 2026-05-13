import pika
import json
from app.core.config import settings

class MessengerService:
    @staticmethod
    def send_notification(message: dict):
        """
        Sends a message to the RabbitMQ queue for background processing.
        Ensures persistent delivery and matches the durable queue contract.
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host='rabbitmq')
            )
            channel = connection.channel()
            
            # Architecture Contract: Must match the Worker's durable=True declaration
            channel.queue_declare(queue='nexcore_notifications', durable=True)

            channel.basic_publish(
                exchange='',
                routing_key='nexcore_notifications',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            connection.close()
        except Exception as e:
            # Logs silently to prevent API crash if broker is unavailable
            print(f"Failed to publish notification: {e}")