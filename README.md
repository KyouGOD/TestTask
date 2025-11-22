Для запуска нужен .env в папке проекта(на одном уровне с src) со следующими значениями:
  
  TG_BOT_API_TOKEN=ваш_токен
  
  REFERENCE_BOOK_FILE_PATH=/app/data/справочник.xlsx

в docker-compose.yml:
  путь на хост системе до справочника(./data:): путь внутри контейнера(/app/data)
                            
после создания .env:
  docker-compose up -d
