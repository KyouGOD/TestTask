Для запуска нужен .env в папке проекта(на одном уровне с src) со следующими значениями:
  
  TG_BOT_API_TOKEN=
  
  REFERENCE_BOOK_FILE_PATH=

в docker-compose.yml:
  путь на хост системе до справочника(./data:): путь внутри контейнера(/app/data)
                            
после создания .env:
  docker-compose up -d
