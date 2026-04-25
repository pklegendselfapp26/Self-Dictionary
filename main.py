import json
import os
import time
import random
import csv
import threading
import requests
import webbrowser
from datetime import datetime, timedelta

from kivy.core.window import Window
from kivy.utils import platform
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import SlideTransition
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast

DATA_FILE = "dictionary_memory.json"
STATS_FILE = "user_stats.json"
RECYCLE_FILE = "recycle_bin.json" 

def get_path(filename):
    try:
        app = MDApp.get_running_app()
        if app and app.user_data_dir:
            return os.path.join(app.user_data_dir, filename)
    except Exception: pass
    return filename

def load_words():
    path = get_path(DATA_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                for w, d in data.items():
                    if "mastery" not in d: d["mastery"] = 0
                    if "image_url" not in d: d["image_url"] = ""
                return data
            except Exception: pass
    return {}

def save_words(data):
    path = get_path(DATA_FILE)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def load_recycle_bin():
    path = get_path(RECYCLE_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                current_time = time.time()
                return {w: d for w, d in data.items() if current_time - d.get("deleted_timestamp", current_time) <= 2592000}
            except Exception: pass
    return {}

def save_recycle_bin(data):
    path = get_path(RECYCLE_FILE)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def speak(text):
    try:
        from plyer import tts
        tts.speak(text)
    except Exception: pass 

class AppLogic:
    @staticmethod
    def update_streak():
        stats = {"last_active": "", "streak": 0, "best_streak": 0}
        path = get_path(STATS_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: stats = json.load(f)
                except Exception: pass
        
        today = datetime.now().date()
        last_date_str = stats.get("last_active", "")
        streak = stats.get("streak", 0)
        best = stats.get("best_streak", 0)

        if last_date_str:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            if today == last_date: pass 
            elif today == last_date + timedelta(days=1): streak += 1
            else: streak = 1 
        else: streak = 1

        if streak > best: best = streak
        stats["last_active"] = today.strftime("%Y-%m-%d")
        stats["streak"] = streak
        stats["best_streak"] = best
        
        with open(path, "w", encoding="utf-8") as f: json.dump(stats, f)
        return streak

def create_empty_state(text, icon="ghost-outline"):
    box = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(250), spacing=dp(10))
    box.add_widget(MDLabel(text="", size_hint_y=None, height=dp(40))) # Spacer
    icon_btn = MDIconButton(icon=icon, icon_size="80sp", pos_hint={"center_x": .5}, theme_text_color="Hint")
    box.add_widget(icon_btn)
    box.add_widget(MDLabel(text=text, halign="center", theme_text_color="Hint", font_style="H6"))
    return box

# --- SCREENS ---

class ViewDictionaryScreen(MDScreen):
    web_dialog = None
    search_input_dialog = None
    active_filter = "All"

    def on_enter(self):
        streak = AppLogic.update_streak()
        if hasattr(self, 'ids') and 'streak_label' in self.ids:
            self.ids.streak_label.text = f"Streak: {streak} Days"
        self.refresh_list()

    def set_filter(self, category):
        self.active_filter = category
        self.refresh_list()

    def play_audio(self, word):
        speak(word.lower())

    def search_word_web(self, word):
        if word: webbrowser.open(f"https://www.google.com/search?q=define+{word.lower()}")

    def open_web_search(self):
        if not self.web_dialog:
            self.search_input_dialog = MDTextField(hint_text="Type word to look up...")
            self.web_dialog = MDDialog(
                title="Google Web Search",
                type="custom",
                content_cls=self.search_input_dialog,
                buttons=[
                    MDFlatButton(text="CLOSE", on_release=lambda x: self.web_dialog.dismiss()),
                    MDRaisedButton(text="SEARCH WEB", md_bg_color=(0.2, 0.7, 0.4, 1), on_release=self.do_web_search)
                ],
            )
        self.search_input_dialog.text = ""
        self.web_dialog.open()

    def do_web_search(self, *args):
        word = self.search_input_dialog.text.strip()
        if word: webbrowser.open(f"https://www.google.com/search?q=define+{word}")
        self.web_dialog.dismiss()

    def delete_word_prompt(self, word_to_delete):
        word_to_delete = word_to_delete.lower()
        self.dialog = MDDialog(
            title="Move to Trash?",
            text=f"Delete '{word_to_delete.capitalize()}'?",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="DELETE", md_bg_color=(0.8, 0.2, 0.2, 1), on_release=lambda x: self.execute_delete(word_to_delete))
            ],
        )
        self.dialog.open()

    def execute_delete(self, word_to_delete):
        self.dialog.dismiss()
        words = load_words()
        if word_to_delete in words:
            deleted_data = words.pop(word_to_delete)
            save_words(words)
            bin_data = load_recycle_bin()
            deleted_data['deleted_timestamp'] = time.time()
            bin_data[word_to_delete] = deleted_data
            save_recycle_bin(bin_data)
            toast(f"Moved to Trash")
            self.refresh_list()

    def edit_word(self, word_to_edit):
        word_to_edit = word_to_edit.lower()
        words = load_words()
        if word_to_edit in words:
            data = words[word_to_edit]
            app = MDApp.get_running_app()
            add_screen = app.root.get_screen('add')
            add_screen.editing_word = word_to_edit
            add_screen.ids.word_input.text = word_to_edit
            add_screen.ids.category_spinner.text = data['category']
            add_screen.ids.meaning_input.text = data['meaning']
            add_screen.ids.example_input.text = data['example']
            app.change_screen('add', direction='left')

    def refresh_list(self, *args):
        if not hasattr(self, 'ids') or 'words_container' not in self.ids: return
        self.ids.words_container.clear_widgets()
        words = load_words()

        if not words:
            self.ids.words_container.add_widget(create_empty_state("Your dictionary is empty!\nClick + ADD to begin.", "book-open-blank-variant"))
            return

        search_query = self.ids.search_input.text.strip().lower() if 'search_input' in self.ids else ""
        sort_mode = self.ids.sort_spinner.text if 'sort_spinner' in self.ids else "Latest"

        filtered = {}
        for w, d in words.items():
            if search_query and search_query not in w: continue
            
            # Apply Filter Chips
            if self.active_filter == "Struggling" and d.get('mastery', 0) >= 3: continue
            elif self.active_filter not in ["All", "Struggling"] and self.active_filter.lower() not in d.get('category', '').lower(): continue
            filtered[w] = d

        if not filtered:
            self.ids.words_container.add_widget(create_empty_state(f"No words match your filter.", "file-search-outline"))
            return

        sorted_items = sorted(filtered.items(), key=lambda i: i[0]) if sort_mode == "Alphabetical" else sorted(filtered.items(), key=lambda i: i[1].get('timestamp', 0), reverse=True)

        from kivy.factory import Factory
        for word, data in sorted_items:
            card = Factory.WordCard()
            card.word_text = word.capitalize()
            card.category_text = data.get('category', 'Uncategorized')
            card.meaning_text = data.get('meaning', '')
            card.example_text = data.get('example', '')
            card.mastery_text = str(data.get('mastery', 0))
            self.ids.words_container.add_widget(card)

class RecycleBinScreen(MDScreen):
    def on_enter(self):
        self.refresh_bin()

    def restore_word(self, word_to_restore):
        bin_data = load_recycle_bin()
        if word_to_restore in bin_data:
            data = bin_data.pop(word_to_restore)
            save_recycle_bin(bin_data)
            words = load_words()
            words[word_to_restore] = data
            save_words(words)
            toast("Word Restored!")
            self.refresh_bin()

    def permanent_delete(self, word_to_delete):
        bin_data = load_recycle_bin()
        if word_to_delete in bin_data:
            del bin_data[word_to_delete]
            save_recycle_bin(bin_data)
            toast("Permanently Deleted")
            self.refresh_bin()

    def empty_bin(self):
        save_recycle_bin({})
        toast("Trash Emptied")
        self.refresh_bin()

    def refresh_bin(self):
        if not hasattr(self, 'ids') or 'bin_container' not in self.ids: return
        self.ids.bin_container.clear_widgets()
        bin_data = load_recycle_bin()
        
        if not bin_data:
            self.ids.bin_container.add_widget(create_empty_state("Recycle Bin is empty.", "delete-empty-outline"))
            return

        from kivy.factory import Factory
        for word, data in bin_data.items():
            card = Factory.RecycleCard()
            card.word_text = word.capitalize()
            card.category_text = data.get('category', 'N/A')
            days_left = 30 - int((time.time() - data.get('deleted_timestamp', time.time())) / 86400)
            card.days_left_text = f"{max(0, days_left)} days left"
            self.ids.bin_container.add_widget(card)

class AddWordScreen(MDScreen):
    editing_word = StringProperty("") 

    def magic_fetch(self):
        word = self.ids.word_input.text.strip().lower()
        if not word:
            toast("Type a word first!")
            return
        toast("Fetching meaning...")
        threading.Thread(target=self._api_call, args=(word,)).start()

    def _api_call(self, word):
        try:
            res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
            if res.status_code == 200:
                data = res.json()[0]
                meanings = data.get("meanings", [])
                
                pos = "Uncategorized"
                def_text = ""
                ex_text = ""
                
                if meanings:
                    pos = meanings[0].get("partOfSpeech", "Uncategorized").capitalize()
                    def_text = meanings[0]["definitions"][0].get("definition", "")
                    
                    # Search all definitions for a valid example sentence
                    for meaning in meanings:
                        for definition in meaning.get("definitions", []):
                            if "example" in definition and definition["example"]:
                                ex_text = definition["example"]
                                break
                        if ex_text:
                            break
                            
                Clock.schedule_once(lambda dt: self._update_ui(pos, def_text, ex_text))
            else:
                Clock.schedule_once(lambda dt: toast("Word not found in API!"))
        except Exception:
            Clock.schedule_once(lambda dt: toast("Network Error. Check connection."))

    def _update_ui(self, pos, def_text, ex_text):
        if pos in self.ids.category_spinner.values:
            self.ids.category_spinner.text = pos
        self.ids.meaning_input.text = def_text
        self.ids.example_input.text = ex_text
        toast("Magic Fetch Complete!")

    def save_word_to_memory(self):
        word = self.ids.word_input.text.strip().lower()
        category = self.ids.category_spinner.text
        meaning = self.ids.meaning_input.text.strip()
        example = self.ids.example_input.text.strip()

        if not word or not meaning:
            toast("Word and Meaning are required.")
            return

        data = load_words()
        if self.editing_word and self.editing_word != word and self.editing_word in data:
            del data[self.editing_word]
        
        old_data = data.get(self.editing_word, {}) if self.editing_word else {}
        
        data[word] = {
            "category": category,
            "meaning": meaning,
            "example": example,
            "timestamp": old_data.get("timestamp", time.time()),
            "mastery": old_data.get("mastery", 0)
        }
        save_words(data)
        toast(f"'{word.capitalize()}' saved!")
        self.clear_inputs()
        MDApp.get_running_app().change_screen('view', direction='right')

    def clear_inputs(self):
        self.ids.word_input.text = ""
        self.ids.meaning_input.text = ""
        self.ids.example_input.text = ""
        self.ids.category_spinner.text = "Uncategorized"
        self.editing_word = ""

class DashboardScreen(MDScreen):
    total_words = StringProperty("0")
    mastered = StringProperty("0")
    struggling = StringProperty("0")
    streak_best = StringProperty("0")
    
    def on_enter(self):
        words = load_words()
        self.total_words = str(len(words))
        self.mastered = str(sum(1 for d in words.values() if d.get('mastery', 0) >= 3))
        self.struggling = str(sum(1 for d in words.values() if d.get('mastery', 0) < 0))
        
        stats = {}
        path = get_path(STATS_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: 
                try: stats = json.load(f)
                except: pass
        self.streak_best = str(stats.get("best_streak", 0))

class SettingsScreen(MDScreen):
    def get_csv_export_path(self):
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                return os.path.join(primary_external_storage_path(), 'Download', 'dictionary_export.csv')
            except: pass
        return get_path('dictionary_export.csv')

    def export_csv(self):
        words = load_words()
        export_path = self.get_csv_export_path()
        try:
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Word', 'Category', 'Meaning', 'Example', 'Mastery'])
                for w, d in words.items():
                    writer.writerow([w, d.get('category',''), d.get('meaning',''), d.get('example',''), d.get('mastery',0)])
            toast(f"Exported to Downloads folder!")
        except Exception:
            MDApp.get_running_app().show_dialog("Error", "Storage permission required.")

    def import_csv(self):
        import_path = self.get_csv_export_path()
        if not os.path.exists(import_path):
            import_path = get_path('dictionary_export.csv')
            if not os.path.exists(import_path):
                toast("No 'dictionary_export.csv' found.")
                return
        words = load_words()
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) 
                for row in reader:
                    if len(row) >= 3:
                        m_score = int(row[4]) if len(row) > 4 and row[4].isdigit() else 0
                        words[row[0].lower()] = {"category": row[1], "meaning": row[2], "example": row[3] if len(row)>3 else "", "mastery": m_score, "timestamp": time.time()}
            save_words(words)
            toast("Words imported successfully!")
        except Exception as e:
            MDApp.get_running_app().show_dialog("Error", str(e))

class TestMenuScreen(MDScreen):
    def check_mcq_unlocked(self):
        if len(load_words()) < 5:
            toast("Save at least 5 words first!")
        else:
            MDApp.get_running_app().change_screen('mcq_test', direction='left')

class FlashcardScreen(MDScreen):
    def on_enter(self):
        all_words = list(load_words().items())
        all_words.sort(key=lambda x: x[1].get('mastery', 0))
        self.test_words = all_words[:15]
        random.shuffle(self.test_words)
        
        self.current_idx = 0
        self.show_current_word()

    def show_current_word(self):
        if not hasattr(self, 'ids'): return
        
        if not self.test_words:
            self.ids.test_word_label.text = "Empty!"
            self.ids.test_meaning_label.text = "Add words first."
            self.ids.reveal_btn.disabled = True
            return
        if self.current_idx >= len(self.test_words):
            self.ids.test_word_label.text = "Done!"
            self.ids.test_meaning_label.text = "Finished!"
            self.ids.reveal_btn.disabled = True
            return
        self.ids.test_word_label.text = self.test_words[self.current_idx][0].capitalize()
        self.ids.test_meaning_label.text = "?"
        self.ids.reveal_btn.disabled = False

    def play_audio(self):
        if self.test_words and self.current_idx < len(self.test_words): speak(self.test_words[self.current_idx][0])

    def reveal_meaning(self):
        if self.current_idx < len(self.test_words):
            data = self.test_words[self.current_idx][1]
            self.ids.test_meaning_label.text = f"Meaning:\n{data.get('meaning', '')}\n\nEx:\n{data.get('example', '')}"
            self.ids.reveal_btn.disabled = True

    def next_word(self):
        self.current_idx += 1
        self.show_current_word()

class MCQScreen(MDScreen):
    def on_enter(self):
        self.all_words = load_words()
        self.word_list = list(self.all_words.keys())
        self.next_question()

    def next_question(self):
        if not hasattr(self, 'ids'): return
        
        self.ids.feedback_label.text = "Choose correct meaning:"
        self.ids.next_btn.disabled = True
        
        struggling_words = [w for w, d in self.all_words.items() if d.get('mastery', 0) < 2]
        if struggling_words and random.random() < 0.7: 
            self.current_word = random.choice(struggling_words)
        else:
            self.current_word = random.choice(self.word_list)
            
        correct_meaning = self.all_words[self.current_word]['meaning']
        
        other_words = [w for w in self.word_list if w != self.current_word]
        random.shuffle(other_words)
        wrong_meanings = [self.all_words[w]['meaning'] for w in other_words[:4]]
        
        self.options = [correct_meaning] + wrong_meanings
        random.shuffle(self.options)
        
        self.ids.mcq_word_label.text = f"{self.current_word.capitalize()}"
        buttons = [self.ids.btn1, self.ids.btn2, self.ids.btn3, self.ids.btn4, self.ids.btn5]
        for i, btn in enumerate(buttons):
            if i < len(self.options):
                btn.text = self.options[i]
                btn.disabled = False
                btn.md_bg_color = MDApp.get_running_app().theme_cls.primary_color
            else:
                btn.disabled = True

    def play_audio(self):
        speak(self.current_word)

    def check_answer(self, selected_button):
        buttons = [self.ids.btn1, self.ids.btn2, self.ids.btn3, self.ids.btn4, self.ids.btn5]
        correct_meaning = self.all_words[self.current_word]['meaning']
        for btn in buttons: btn.disabled = True

        if selected_button.text == correct_meaning:
            self.ids.feedback_label.text = "CORRECT! +1 Mastery"
            selected_button.md_bg_color = [0.2, 0.8, 0.2, 1] 
            self.all_words[self.current_word]['mastery'] += 1
        else:
            self.ids.feedback_label.text = "INCORRECT! -1 Mastery"
            selected_button.md_bg_color = [0.8, 0.2, 0.2, 1] 
            for btn in buttons:
                if btn.text == correct_meaning: btn.md_bg_color = [0.2, 0.8, 0.2, 1]
            self.all_words[self.current_word]['mastery'] -= 1

        save_words(self.all_words) 
        self.ids.next_btn.disabled = False

# --- APP CLASS ---

class SelfDictionaryApp(MDApp):
    dialog = None

    def build(self):
        self.theme_cls.theme_style = "Dark" 
        self.theme_cls.primary_palette = "Indigo"
        Window.bind(on_keyboard=self.hook_keyboard)
        # 🟢 THE KEYBOARD FIX: This forces the screen to slide up above the keyboard 🟢
        Window.softinput_mode = "below_target" 
        return Builder.load_file("main.kv")

    def on_start(self):
        stats = {}
        path = get_path(STATS_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: stats = json.load(f)
                except: pass
        saved_theme = stats.get("theme", "Police")
        self.change_theme(saved_theme)

    def change_theme(self, theme_name):
        if theme_name == "White (Sadabahar)":
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Blue"
        elif theme_name == "Dark":
            self.theme_cls.theme_style = "Dark"
            self.theme_cls.primary_palette = "DeepPurple"
        elif theme_name == "Police":
            self.theme_cls.theme_style = "Dark"
            self.theme_cls.primary_palette = "Indigo"
        elif theme_name == "Cool & Composed":
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Teal"
        elif theme_name == "R E A L E L":
            self.theme_cls.theme_style = "Dark"
            self.theme_cls.primary_palette = "Orange"
        else:
            self.theme_cls.theme_style = "Dark"
            self.theme_cls.primary_palette = "Indigo"
        
        path = get_path(STATS_FILE)
        stats = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: stats = json.load(f)
                except: pass
        stats["theme"] = theme_name
        with open(path, "w", encoding="utf-8") as f: json.dump(stats, f)

    def change_screen(self, screen_name, direction='left'):
        self.root.transition = SlideTransition(direction=direction)
        self.root.current = screen_name

    def hook_keyboard(self, window, key, *args):
        if key == 27:
            if self.root.current == 'view': return False
            elif self.root.current in ['flashcard', 'mcq_test']: self.change_screen('test_menu', direction='right')
            else: self.change_screen('view', direction='right')
            return True
        return False

    def show_dialog(self, title, message):
        if self.dialog: self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

if __name__ == "__main__":
    SelfDictionaryApp().run()
