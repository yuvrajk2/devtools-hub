"""Page copy for each tool: a short explanation and FAQ. Rendered under the tool and
emitted as FAQPage JSON-LD for search engines. Keep answers short and accurate."""

CONTENT = {
    "json": {
        "about": "Paste JSON to check that it is valid, pretty-print it with 2 or 4 spaces or a tab, or minify it to a single line. When the JSON is invalid, the error points to the line and column.",
        "faq": [
            ("Why is my JSON invalid?", "The usual causes are trailing commas, single quotes instead of double quotes, unquoted keys and comments. JSON allows none of these."),
            ("What is the difference between format and minify?", "Formatting adds line breaks and indentation so people can read the data. Minifying removes all optional whitespace to make it smaller."),
        ],
    },
    "base64": {
        "about": "Encode text to Base64 or decode Base64 back to text. Text is handled as UTF-8, so accents and emoji survive the round trip.",
        "faq": [
            ("Is Base64 encryption?", "No. Base64 is an encoding, not encryption. Anyone can decode it, so never use it to protect secrets."),
            ("What is URL-safe Base64?", "It replaces + and / with - and _ and usually drops the = padding, so the result can sit safely in URLs and filenames."),
        ],
    },
    "url": {
        "about": "Percent-encode text so it can be used safely in a URL or query string, or decode percent-encoded text back to readable form.",
        "faq": [
            ("What is percent-encoding?", "Characters that are not safe in a URL are replaced by a percent sign and two hex digits, so a space becomes %20."),
            ("Does this encode a whole URL?", "It encodes every reserved character, which is right for a query value or path segment. Encoding a full URL would also escape its : and / characters, so encode only the part that needs it."),
        ],
    },
    "jwt": {
        "about": "Decode a JSON Web Token to read its header and payload, including issued-at and expiry times, and see whether it has expired. The signature is not verified.",
        "faq": [
            ("What is a JWT?", "A JSON Web Token is a string of three Base64URL parts: header, payload and signature. It is commonly used for login sessions and API access."),
            ("Does this verify the signature?", "No. It only decodes the header and payload. Decoding shows what a token claims, but only a check with the right key proves it is genuine."),
            ("Is it safe to paste a token here?", "Treat tokens like passwords. This tool does not store input, but avoid pasting live production tokens into any online tool."),
        ],
    },
    "hash": {
        "about": "Generate MD5, SHA-1, SHA-256 and SHA-512 hashes of any text at once.",
        "faq": [
            ("Can a hash be reversed?", "No. A hash is one-way. Attackers guess inputs and compare the resulting hashes instead."),
            ("Which hash should I use?", "Use SHA-256 or SHA-512 for integrity checks. MD5 and SHA-1 are broken for security use and only belong in legacy systems. For passwords use a slow algorithm such as bcrypt or Argon2, not a plain hash."),
        ],
    },
    "uuid": {
        "about": "Generate random version 4 UUIDs, one or hundreds at a time, in lowercase or uppercase and with or without dashes.",
        "faq": [
            ("What is a version 4 UUID?", "A UUID built from random numbers. It has 122 random bits, so collisions are practically impossible."),
            ("Can I use a UUID as a secret?", "A UUID is an identifier, not a secret. Use a proper token generator for anything that must stay private."),
        ],
    },
    "qr": {
        "about": "Turn text or a URL into a QR code, choose an error-correction level, and download it as a scalable SVG that stays sharp at any size.",
        "faq": [
            ("What does error correction do?", "Higher levels (L, M, Q, H) let a code still scan when part of it is damaged or covered, at the cost of a denser pattern. M is a good default."),
            ("Why do I get a too long error?", "A QR code holds a limited amount of data, and higher error-correction levels hold less. Shorten the text or lower the level."),
        ],
    },
    "color": {
        "about": "Convert a color between HEX, RGB and HSL, and build a CSS linear-gradient from two colors and an angle.",
        "faq": [
            ("How do HEX, RGB and HSL relate?", "They describe the same color three ways. HEX and RGB mix red, green and blue. HSL uses hue, saturation and lightness, which is easier to adjust by hand."),
            ("What does the gradient angle mean?", "0deg points up, 90deg points right and 180deg points down. The colors blend along that direction."),
        ],
    },
    "time": {
        "about": "Convert Unix timestamps in seconds or milliseconds, or ISO 8601 dates, into ISO, Unix and RFC 2822 formats. Leave the box empty to see the current time.",
        "faq": [
            ("What is a Unix timestamp?", "The number of seconds since 1 January 1970 UTC. Many systems use milliseconds instead, so very large numbers are treated as milliseconds."),
            ("Which time zone is used?", "All results are in UTC. A date without a time zone is treated as UTC."),
        ],
    },
    "diff": {
        "about": "Paste two versions of a text to see which lines were removed and which were added, with a few lines of context around each change.",
        "faq": [
            ("How does the comparison work?", "It compares the two texts line by line. Removed lines start with a minus and added lines with a plus."),
            ("Does whitespace matter?", "Yes. A trailing space or a different indent makes a line count as changed."),
        ],
    },
    "password": {
        "about": "Generate strong random passwords with your choice of length and character types, using Python's secrets module and the operating system's secure random source. Nothing is stored.",
        "faq": [
            ("How long should a password be?", "Length matters most. 16 or more random characters is a strong default for accounts protected by a password manager."),
            ("Is it safe to use a password generated on a website?", "Nothing is stored here, but the password travels over the network. A password manager's built-in generator never sends it anywhere, so prefer that for your most important accounts."),
        ],
    },
    "lorem": {
        "about": "Generate lorem ipsum placeholder paragraphs for layouts and mockups.",
        "faq": [
            ("What is lorem ipsum?", "Placeholder text used so a design can be judged without real copy. It is scrambled Latin."),
            ("Is it real Latin?", "It is derived from a work by Cicero, but the words are shuffled and mostly meaningless."),
        ],
    },
    "case": {
        "about": "Convert text to UPPER CASE, lower case, Title Case, camelCase, PascalCase, snake_case, kebab-case and CONSTANT_CASE in one go.",
        "faq": [
            ("What is the difference between camelCase and PascalCase?", "camelCase starts with a lowercase letter, like myVariableName. PascalCase starts with an uppercase letter, like MyVariableName."),
            ("When do I use snake_case or kebab-case?", "snake_case is common in Python and databases. kebab-case is common in URLs and CSS class names."),
        ],
    },
    "currency": {
        "about": "Convert between more than 150 currencies. Edit any amount and press Enter, and every other currency updates at once. Add more currencies by typing their three-letter codes. Rates come from ExchangeRate-API, are cached on the server, and are daily reference rates.",
        "faq": [
            ("How often are the exchange rates updated?", "The free data source publishes new rates once a day, so these are daily reference rates, not live trading quotes. Banks and card networks add their own margins, so the rate you actually get will differ."),
            ("How do I add another currency?", "Type its three-letter code, such as NPR or AED, into the Add currencies box and press Enter. Any currency in the supported list can be added."),
        ],
    },
    "units": {
        "about": "Pick a category, type a value into any field and press Enter. All the other units update at once, so there is no source and target to choose. Categories: length, weight, temperature, volume, area, speed, time, data size and pressure.",
        "faq": [
            ("How accurate are the conversions?", "They use exact definitions where they exist, such as 1 inch = 25.4 mm and 1 lb = 0.45359237 kg, and are calculated in 64-bit floating point and shown to 10 significant digits."),
            ("What is the difference between MB and MiB?", "A megabyte (MB) is 1,000,000 bytes. A mebibyte (MiB) is 1,048,576 bytes (1024 squared). Operating systems and drive makers mix the two, which is why a disk can look smaller than advertised."),
        ],
    },
}
