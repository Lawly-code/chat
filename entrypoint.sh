#!/bin/sh
set -e

# Проверяем, что RabbitMQ доступен
until nc -z rabbitmq 5672 || nc -z test_rabbitmq 5672; do
  echo "RabbitMQ недоступен - ожидание..."
  sleep 1
done

echo "RabbitMQ доступен - запуск приложения!"

exec "$@"
