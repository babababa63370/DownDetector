from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

Window.size = (400, 600)

class MonApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0

    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Titre
        title = Label(text='Ma Premier App', size_hint_y=0.2, font_size='32sp')
        layout.add_widget(title)
        
        # Compteur
        self.counter_label = Label(text='0', size_hint_y=0.4, font_size='60sp', color=(0, 0.5, 1, 1))
        layout.add_widget(self.counter_label)
        
        # Bouton
        btn = Button(text='Appuyez-moi', size_hint_y=0.2, font_size='18sp')
        btn.bind(on_press=self.increment)
        layout.add_widget(btn)
        
        return layout

    def increment(self, instance):
        self.count += 1
        self.counter_label.text = str(self.count)

if __name__ == '__main__':
    MonApp().run()
