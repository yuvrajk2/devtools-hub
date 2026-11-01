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
    "cidr": {
        "about": "Enter an IPv4 or IPv6 address with a prefix (192.168.1.0/24) or a netmask to see the network, mask, wildcard, broadcast, first and last host, and how many hosts fit. Optionally check whether another address falls inside the network.",
        "faq": [
            ("What does /24 mean?", "The prefix length is how many leading bits identify the network. A /24 leaves 8 bits for hosts, so 256 addresses, of which 254 are usable on IPv4."),
            ("Why are two addresses not usable?", "On IPv4 subnets up to /30, the first address is the network address and the last is the broadcast address. /31 and /32 are special cases with no such reservation."),
        ],
    },
    "regex": {
        "about": "Test a regular expression against sample text, with matches highlighted and capture groups listed. Patterns run with Python's re engine in a separate sandboxed process with a 2 second limit, so a runaway pattern cannot hang the site.",
        "faq": [
            ("Which regex flavor is this?", "Python's re module. Most syntax matches JavaScript and PCRE, but features like lookbehind rules and named groups (?P<name>...) differ slightly between flavors."),
            ("Why did my pattern time out?", "Nested quantifiers such as (a+)+$ can take exponential time on some inputs, called catastrophic backtracking. Make the pattern more specific or remove the nesting."),
        ],
    },
    "cron": {
        "about": "Paste a 5-field cron expression to see what each field means and when it runs next. Supports lists, ranges, steps, month and weekday names, and shortcuts like @daily. All times are UTC.",
        "faq": [
            ("What are the five cron fields?", "Minute, hour, day of month, month and day of week, in that order. A star means every value."),
            ("What happens when both day fields are set?", "In classic cron, a job runs when either the day of month or the day of week matches, not both."),
        ],
    },
    "pdf_merge": {
        "about": 'Combine two or more PDF files into a single document. Pick the files in the order you want them joined. Files are processed in memory and never saved.',
        "faq": [('Can I reorder the files?', 'Files are joined in the order you select them. To change the order, select them again in the order you want.'), ('Is there a size limit?', 'Uploads are limited to the size shown on the page, and the merged file can have up to 1,000 pages.')],
    },
    "pdf_split": {
        "about": 'Split a PDF into several files by custom page ranges, one file per page, or every N pages. You get a ZIP containing the parts.',
        "faq": [('How do I write page ranges?', 'Use commas between ranges: 1-3,4-6,7- makes three files. A trailing dash means to the end, and the word last means the final page.'), ('Can I split every page?', 'Yes. Choose every page as its own PDF and you get one file per page in a ZIP.')],
    },
    "pdf_extract": {
        "about": 'Pull the pages you want out of a PDF into a new file. Pages come out in the order you type them, so this also reorders pages.',
        "faq": [('Can I reorder pages?', 'Yes. Entering 3,1,2 produces a PDF with page 3 first, then page 1, then page 2.'), ('Can I reverse a range?', 'Yes. 5-1 runs backwards from page 5 to page 1.')],
    },
    "pdf_delete": {
        "about": 'Remove unwanted pages from a PDF and download the rest. Enter single pages or ranges such as 2,4-6.',
        "faq": [('Can I delete every page?', 'No. At least one page must remain.'), ('Does deleting pages change the rest of the document?', 'No. The remaining pages are copied as they are, in their original order.')],
    },
    "pdf_rotate": {
        "about": 'Rotate every page, or only the pages you choose, by 90, 180 or 270 degrees clockwise.',
        "faq": [('How do I rotate only some pages?', 'Type the pages, such as 2,4-6. Leave the box empty to rotate the whole document.'), ('Is the rotation permanent?', "The saved file displays the pages rotated. The page content is not altered, only the page's rotation setting.")],
    },
    "pdf_compress": {
        "about": 'Make a PDF smaller. Lossless mode re-compresses page content and removes duplicate data without changing quality. Medium and strong modes also re-encode JPEG images at lower quality.',
        "faq": [('How much smaller will it get?', 'It depends on the file. PDFs full of photos shrink the most. PDFs that are mostly text are often already compact, and in that case you get the original back.'), ('Is it lossless?', 'Only the lossless option. Medium and strong lower the quality of JPEG images to save space.')],
    },
    "pdf_protect": {
        "about": 'Add a password to a PDF using AES-256 encryption, so it can only be opened with the password.',
        "faq": [('How strong is the protection?', 'AES-256 is strong, but the password is the weak point. Use a long, unique one and store it in a password manager.'), ('Is the password stored?', 'No. It is used to encrypt the file in memory and then discarded.')],
    },
    "pdf_unlock": {
        "about": 'Remove the password from a PDF you own, once you provide the correct password.',
        "faq": [('Can this crack a forgotten password?', 'No. It only removes protection when you already know the password.'), ('Is it legal to unlock a PDF?', 'Only use it on files you own or have permission to unlock.')],
    },
    "img2pdf": {
        "about": "Turn JPG, PNG, WebP and other images into a single PDF with one image per page, either at each image's own size or on A4 pages with margins.",
        "faq": [('Which image formats work?', 'JPG, PNG, WebP, GIF, BMP and TIFF. Transparent areas become white.'), ('Will the photos be rotated correctly?', 'Yes. The orientation stored in a photo is applied before it is added to the PDF.')],
    },
    "pdf_info": {
        "about": 'See how many pages a PDF has, its page size, version, whether it is password-protected, and its metadata such as title, author and creation date.',
        "faq": [('Where does the metadata come from?', "From the PDF's own document information. Many files leave fields like author empty."), ('Is the file stored?', 'No. It is read in memory to produce this summary and then discarded.')],
    },
}
