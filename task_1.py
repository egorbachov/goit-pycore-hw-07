import sys
from collections import UserDict
from datetime import datetime, date, timedelta

DATE_FORMAT = "%d.%m.%Y"
PHONE_LENGTH = 10
UPCOMING_DAYS = 7


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    def __init__(self, value):
        name = str(value).strip()
        if not name:
            raise ValueError("Name cannot be empty.")
        super().__init__(name)


class Phone(Field):
    def __init__(self, value):
        phone = str(value).strip()
        if not (phone.isdigit() and len(phone) == PHONE_LENGTH):
            raise ValueError(f"Phone number must contain {PHONE_LENGTH} digits.")
        super().__init__(phone)


class Birthday(Field):
    def __init__(self, value):
        try:
            birthday = datetime.strptime(str(value).strip(), DATE_FORMAT).date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

        if birthday > date.today():
            raise ValueError("Birthday cannot be in the future.")

        super().__init__(birthday)

    def __str__(self):
        return self.value.strftime(DATE_FORMAT)


class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        new_phone = Phone(phone)
        if self.find_phone(new_phone.value):
            raise ValueError(f"Phone {new_phone.value} already exists for {self.name.value}.")
        self.phones.append(new_phone)

    def remove_phone(self, phone):
        found = self.find_phone(phone)
        if found:
            self.phones.remove(found)

    def edit_phone(self, old_phone, new_phone):
        found = self.find_phone(old_phone)
        if not found:
            raise ValueError(f"Phone {old_phone} not found.")
        index = self.phones.index(found)
        self.phones[index] = Phone(new_phone)

    def find_phone(self, phone):
        for p in self.phones:
            if p.value == str(phone).strip():
                return p
        return None

    def add_birthday(self, birthday):
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones) or "no phones"
        birthday = f", birthday: {self.birthday}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones}{birthday}"


class AddressBook(UserDict):
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(str(name).strip())

    def delete(self, name):
        if name in self.data:
            del self.data[name]

    @staticmethod
    def _birthday_this_year(birthday, today):
        """Найближча дата святкування з урахуванням 29 лютого."""
        for year in (today.year, today.year + 1):
            try:
                candidate = birthday.replace(year=year)
            except ValueError:  # 29 лютого у невисокосному році
                candidate = date(year, 3, 1)
            if candidate >= today:
                return candidate
        return candidate

    @staticmethod
    def _move_from_weekend(day):
        """Якщо дата випадає на вихідні, переносимо привітання на понеділок."""
        if day.weekday() >= 5:  # 5 - субота, 6 - неділя
            return day + timedelta(days=7 - day.weekday())
        return day

    def get_upcoming_birthdays(self, days=UPCOMING_DAYS):
        """Контакти, яких треба привітати протягом наступних days днів."""
        today = date.today()
        upcoming = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            celebration = self._birthday_this_year(record.birthday.value, today)
            if 0 <= (celebration - today).days <= days:
                upcoming.append(
                    {
                        "name": record.name.value,
                        "congratulation_date": self._move_from_weekend(celebration).strftime(DATE_FORMAT),
                    }
                )

        upcoming.sort(key=lambda item: datetime.strptime(item["congratulation_date"], DATE_FORMAT))
        return upcoming


ARG_HINTS = {
    "add_contact": "Give me name and phone please.",
    "change_contact": "Give me name, old phone and new phone please.",
    "add_birthday": "Give me name and birthday (DD.MM.YYYY) please.",
}


def input_error(func):
    hint = ARG_HINTS.get(func.__name__, "Enter the argument for the command")

    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            if str(e) and not str(e).startswith("not enough values to unpack"):
                return str(e)
            return hint
        except KeyError:
            return "Contact not found."
        except IndexError:
            return hint

    inner.__name__ = func.__name__
    return inner


def parse_input(user_input):
    if not user_input.strip():
        return "", []
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, args


@input_error
def add_contact(args, book):
    name, phone, *_ = args
    Phone(phone)  # перевіряємо номер до створення контакту

    record = book.find(name)
    message = "Contact updated."

    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."

    record.add_phone(phone)
    return message


@input_error
def change_contact(args, book):
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args, book):
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return f"{record.name.value} has no phone numbers yet."
    return f"{record.name.value}: " + "; ".join(p.value for p in record.phones)


@input_error
def show_all(book):
    if not book.data:
        return "No contacts saved."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args, book):
    name, birthday, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args, book):
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError
    if record.birthday is None:
        return f"{record.name.value} has no birthday set."
    return f"{record.name.value}: {record.birthday}"


@input_error
def birthdays(book):
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays in the next week."
    return "\n".join(f"{item['name']}: {item['congratulation_date']}" for item in upcoming)


HELP_TEXT = """Available commands:
  hello                                  - greet the bot
  add [name] [phone]                     - add a contact or a phone to a contact
  change [name] [old phone] [new phone]  - change a contact's phone number
  phone [name]                           - show a contact's phone numbers
  all                                    - show all contacts
  add-birthday [name] [DD.MM.YYYY]       - add a birthday to a contact
  show-birthday [name]                   - show a contact's birthday
  birthdays                              - birthdays in the next 7 days
  help                                   - show this message
  close / exit                           - close the program"""


def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        try:
            user_input = input("Enter a command: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGood bye!")
            break

        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "help":
            print(HELP_TEXT)
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact(args, book))
        elif command == "phone":
            print(show_phone(args, book))
        elif command == "all":
            print(show_all(book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(book))
        elif command == "":
            continue
        else:
            print("Invalid command.")


def demo():
    # Демо роботи AddressBook згідно з прикладом у завданні
    book = AddressBook()

    john_record = Record("John")
    john_record.add_phone("1234567890")
    john_record.add_phone("5555555555")
    book.add_record(john_record)

    jane_record = Record("Jane")
    jane_record.add_phone("9876543210")
    book.add_record(jane_record)

    for name, record in book.data.items():
        print(record)

    john = book.find("John")
    john.edit_phone("1234567890", "1112223333")
    print(john)

    found_phone = john.find_phone("5555555555")
    print(f"{john.name}: {found_phone}")

    # Демо роботи з днями народження
    today = date.today()
    john.add_birthday((today + timedelta(days=3)).replace(year=1990).strftime(DATE_FORMAT))
    jane_record.add_birthday((today + timedelta(days=1)).replace(year=1985).strftime(DATE_FORMAT))
    print(john)

    print("Upcoming birthdays:")
    for item in book.get_upcoming_birthdays():
        print(f"  {item['name']}: {item['congratulation_date']}")

    book.delete("Jane")


if __name__ == "__main__":
    # За замовчуванням запускаємо бота, з аргументом demo - демонстрацію AddressBook
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        main()
