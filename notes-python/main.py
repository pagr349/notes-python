import sqlite3
import bcrypt
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Rectangle, Color


# Initialize Database
def init_db():
    with sqlite3.connect("notes.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()


# --- Base Screen with Purple Background ---
class PurpleScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        with layout.canvas.before:
            Color(0.3, 0, 0.4, 1)
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
            layout.bind(size=self._update_rect, pos=self._update_rect)

        self.add_widget(layout)
        self.layout = layout

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


# --- Login Screen ---
class LoginScreen(PurpleScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.username_input = TextInput(hint_text="Username", multiline=False)
        self.password_input = TextInput(hint_text="Password", password=True, multiline=False)

        login_button = Button(text="Login", on_press=self.login)
        signup_button = Button(text="Sign Up", on_press=lambda x: setattr(self.manager, "current", "signup"))

        self.layout.add_widget(Label(text="Login", font_size=50, color=(1, 1, 1, 1), bold=True))
        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)
        self.layout.add_widget(login_button)
        self.layout.add_widget(signup_button)

    def login(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()

        with sqlite3.connect("notes.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username=?", (username,))
            user = cursor.fetchone()

        if user:
            stored_hashed_password = user[1]
            if bcrypt.checkpw(password.encode(), stored_hashed_password.encode()):
                App.get_running_app().current_user_id = user[0]
                print("✅ Successfully logged in!")
                self.manager.get_screen("notes").load_notes()
                self.manager.current = "notes"
            else:
                print("❌ Incorrect password!")
        else:
            print("❌ User not found!")


# --- Signup Screen ---
class SignupScreen(PurpleScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.username_input = TextInput(hint_text="Choose a username", multiline=False)
        self.password_input = TextInput(hint_text="Choose a password", password=True, multiline=False)

        signup_button = Button(text="Sign Up", on_press=self.signup)
        login_button = Button(text="Back to Login", on_press=lambda x: setattr(self.manager, "current", "login"))

        self.layout.add_widget(Label(text="Sign Up", font_size=50, color=(1, 1, 1, 1), bold=True))
        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)
        self.layout.add_widget(signup_button)
        self.layout.add_widget(login_button)

    def signup(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        try:
            with sqlite3.connect("notes.db") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            print("✅ Account created! Redirecting to login.")
            self.manager.current = "login"
        except sqlite3.IntegrityError:
            print("❌ Username already taken")


# --- Notes Screen ---
class NotesScreen(PurpleScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

        title = Label(text="YOUR NOTES", font_size=50, color=(1, 1, 1, 1), bold=True)

        self.note_input = TextInput(
            hint_text="Write your note here...",
            size_hint=(1, 0.3),
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1)
        )

        save_button = Button(text="Save Note", size_hint=(1, 0.2), on_press=self.save_note)
        logout_button = Button(text="Logout", size_hint=(1, 0.2), on_press=self.logout)

        self.scroll_view = ScrollView(size_hint=(1, 0.5))
        self.notes_container = GridLayout(cols=1, size_hint_y=None, spacing=10, padding=10)
        self.notes_container.bind(minimum_height=self.notes_container.setter("height"))
        self.scroll_view.add_widget(self.notes_container)

        self.layout.add_widget(title)
        self.layout.add_widget(self.note_input)
        self.layout.add_widget(save_button)
        self.layout.add_widget(logout_button)
        self.layout.add_widget(self.scroll_view)

    def on_pre_enter(self):
        if App.get_running_app().current_user_id is None:
            print("⚠ No user logged in! Redirecting to login.")
            self.manager.current = "login"
        else:
            self.load_notes()

    def save_note(self, instance):
        user_id = App.get_running_app().current_user_id
        content = self.note_input.text.strip()
        if content:
            try:
                with sqlite3.connect("notes.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO notes (user_id, content) VALUES (?, ?)", (user_id, content))
                    conn.commit()
                self.note_input.text = ""
                self.load_notes()
            except Exception as e:
                print(f"⚠ Error saving note: {e}")

    def load_notes(self):
        self.notes_container.clear_widgets()
        user_id = App.get_running_app().current_user_id

        try:
            with sqlite3.connect("notes.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, content FROM notes WHERE user_id=?", (user_id,))
                notes = cursor.fetchall()

            for note_id, content in notes:
                note_label = Label(text=content, size_hint_x=0.9, color=(1, 1, 1, 1))
                delete_button = Button(text="🗑", size_hint_x=0.1, on_press=lambda btn, nid=note_id: self.delete_note(nid))
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
                row.add_widget(note_label)
                row.add_widget(delete_button)
                self.notes_container.add_widget(row)
        except Exception as e:
            print(f"⚠ Error loading notes: {e}")

    def delete_note(self, note_id):
        try:
            with sqlite3.connect("notes.db") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE id=?", (note_id,))
                conn.commit()
            self.load_notes()
        except Exception as e:
            print(f"⚠ Error deleting note: {e}")

    def logout(self, instance):
        App.get_running_app().current_user_id = None
        self.manager.current = "login"


# --- Main App ---
class NotesApp(App):
    current_user_id = None

    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(SignupScreen(name="signup"))
        sm.add_widget(NotesScreen(name="notes"))
        return sm


if __name__ == "__main__":
    init_db()
    NotesApp().run()
