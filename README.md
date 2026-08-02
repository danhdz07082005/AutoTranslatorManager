# Auto Translator Manager

A smart, open-source centralized launcher for auto-translating games (Unity, RenPy) without polluting game directories.

Auto Translator Manager (ATM) is designed to separate the translation engine (like XUnity.AutoTranslator) from your game directory. It dynamically injects the translation runtime into the game only when you play, ensuring your game files remain 100% clean. It features a robust plugin system, allowing you to seamlessly swap between translation engines (DeepL, Google, etc.).

## 🚀 Quick Start

1. **Download:** Grab the latest `AutoTranslator.exe` from the [Releases](../../releases) page.
2. **Launch:** Run the executable. No Python installation required.
3. **Add Game:** Point the launcher to your game's `.exe` file.
4. **Play:** Click "Start" and enjoy your auto-translated game!

## 📚 Documentation

For detailed guides, please refer to the `docs/` folder:

- [Installation Guide](docs/installation.md)
- [Architecture Overview](docs/architecture.md)
- [Plugin Development Guide](docs/plugin-development.md)
- [Frequently Asked Questions (FAQ)](docs/faq.md)

## 🛠️ Built With

- **Python 3.12+**
- **CustomTkinter** for a modern, dark-themed UI.
- **Pytest** for end-to-end testing.
- **Ruff, Black, MyPy** for code quality.

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. 

Please read our [PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) for details on our code of conduct, and the process for submitting pull requests to us.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
