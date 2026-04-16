import customtkinter as ctk

from settings.settings_manager import settings_manager


class FirstRunWizard(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("First time setup")
        self.geometry("520x560")
        self.minsize(480, 520)
        self.resizable(False, False)

        self._done = False

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Welcome",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 6))

        ctk.CTkLabel(
            self,
            text="Choose your preferences once — you can still change them later by voice commands.",
            text_color="#a1a1aa",
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 18))

        card = ctk.CTkFrame(self, corner_radius=16)
        card.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        # Username
        ctk.CTkLabel(card, text="Your name", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 6)
        )
        self._name = ctk.CTkEntry(card, placeholder_text="e.g., Ahmed")
        self._name.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        # Language
        ctk.CTkLabel(card, text="Language", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 6)
        )
        self._lang = ctk.StringVar(value=settings_manager.language)
        ctk.CTkOptionMenu(card, values=["ar-EG", "en-US"], variable=self._lang).grid(
            row=3, column=0, sticky="ew", padx=18, pady=(0, 14)
        )

        # Voice gender
        ctk.CTkLabel(card, text="Voice", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=4, column=0, sticky="w", padx=18, pady=(0, 6)
        )
        self._gender = ctk.StringVar(value=settings_manager.voice_gender)
        ctk.CTkOptionMenu(card, values=["female", "male"], variable=self._gender).grid(
            row=5, column=0, sticky="ew", padx=18, pady=(0, 14)
        )

        # Speed
        ctk.CTkLabel(card, text="Speech speed", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=6, column=0, sticky="w", padx=18, pady=(0, 6)
        )
        self._speed = ctk.DoubleVar(value=settings_manager.speech_speed)
        self._speed_label = ctk.CTkLabel(card, text=f"{settings_manager.speech_speed:.2f}x", text_color="#c4b5fd")
        self._speed_label.grid(row=7, column=0, sticky="w", padx=18, pady=(0, 6))
        ctk.CTkSlider(
            card,
            from_=settings_manager.min_speech_speed,
            to=settings_manager.max_speech_speed,
            variable=self._speed,
            command=self._on_speed,
        ).grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 18))

        self._error = ctk.CTkLabel(card, text="", text_color="#fecaca")
        self._error.grid(row=9, column=0, sticky="w", padx=18, pady=(0, 10))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 20))
        btns.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btns, text="Continue", command=self._submit).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(btns, text="Cancel", fg_color="#2b2f36", command=self._cancel).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        self.grab_set()
        self.focus_set()

    def _on_speed(self, value: float) -> None:
        self._speed_label.configure(text=f"{float(value):.2f}x")

    def _submit(self) -> None:
        name = (self._name.get() or "").strip()
        if not name:
            self._error.configure(text="Please enter your name")
            return

        # Apply + persist
        settings_manager.set_username(name)
        settings_manager.set_language(self._lang.get())
        settings_manager.set_voice_gender(self._gender.get())
        settings_manager.set_speech_speed(float(self._speed.get()))

        self._done = True
        self.destroy()

    def _cancel(self) -> None:
        self._done = False
        self.destroy()

    @property
    def done(self) -> bool:
        return self._done
