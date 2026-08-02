import customtkinter as ctk

class SettingsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Grid cho Settings
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # General Settings
        self.lbl_settings = ctk.CTkLabel(self, text="Global Settings", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_settings.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.switch_dark_mode = ctk.CTkSwitch(self, text="Dark Mode", command=self.toggle_dark_mode)
        self.switch_dark_mode.select()
        self.switch_dark_mode.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        self.switch_auto_update = ctk.CTkSwitch(self, text="Auto Update Plugins")
        self.switch_auto_update.select()
        self.switch_auto_update.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        # Marketplace
        self.lbl_market = ctk.CTkLabel(self, text="Plugin Marketplace", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_market.grid(row=0, column=1, padx=20, pady=20, sticky="w")
        
        self.market_frame = ctk.CTkScrollableFrame(self)
        self.market_frame.grid(row=1, column=1, rowspan=3, padx=20, pady=10, sticky="nsew")
        
        self.lbl_plugin = ctk.CTkLabel(self.market_frame, text="DeepL Translator (Official)\nStatus: Not Installed")
        self.lbl_plugin.pack(pady=10)
        
        self.btn_install = ctk.CTkButton(self.market_frame, text="Install Plugin")
        self.btn_install.pack(pady=5)
        
    def toggle_dark_mode(self):
        if self.switch_dark_mode.get():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
