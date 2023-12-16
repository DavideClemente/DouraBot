import json
from datetime import datetime


class MongoSimulator:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load_data()

    def load_data(self):
        try:
            with open(self.file_path, 'r') as file:
                # Deserialize dates from ISO format
                data = json.load(file, object_hook=self.date_decoder)
                return data
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            # Create an empty data structure if the file doesn't exist or is not valid JSON
            return []

    def save_data(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=2, default=self.date_encoder)

    def insert_document(self, name: str, birthday_date: str):
        document = {
            'name': name,
            'birthday_date': birthday_date,
            'timestamp': datetime.utcnow()
        }
        self.data.append(document)
        self.save_data()

    def find_documents(self, target_date):
        target_day_month = self.extract_day_month(target_date)
        # Search for birthdays matching the target date
        matching_birthdays = [
            document for document in self.data
            if self.extract_day_month(document.get('birthday_date')) == target_day_month
        ]
        return matching_birthdays

    def extract_day_month(self, date_str):
        # Convert the date string to a datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        # Format and return the day and month components
        return date_obj.strftime('%d-%m')

    @staticmethod
    def date_encoder(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

    @staticmethod
    def date_decoder(obj):
        if 'timestamp' in obj:
            obj['timestamp'] = datetime.fromisoformat(obj['timestamp'])
        return obj
