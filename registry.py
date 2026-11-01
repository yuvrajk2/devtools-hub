"""The list of tools. To add one: put it here, write its route in tools/, and add its FAQ in content.py."""

GROUPS = [
    ("Convert", [("currency", "Currency"), ("units", "Units"), ("time", "Timestamp"), ("case", "Case Convert"), ("color", "Color")]),
    ("PDF", [("pdf_merge", "Merge PDF"), ("pdf_split", "Split PDF"), ("pdf_extract", "Extract Pages"),
             ("pdf_delete", "Delete Pages"), ("pdf_rotate", "Rotate PDF"), ("pdf_compress", "Compress PDF"),
             ("pdf_protect", "Protect PDF"), ("pdf_unlock", "Unlock PDF"), ("img2pdf", "Images to PDF"),
             ("pdf_info", "PDF Info")]),
    ("Developer", [("json", "JSON"), ("base64", "Base64"), ("url", "URL Encode"), ("jwt", "JWT Decoder"),
                   ("hash", "Hashes"), ("uuid", "UUID"), ("qr", "QR Code"), ("diff", "Text Diff"), ("cidr", "CIDR"),
                   ("regex", "Regex"), ("cron", "Cron"), ("password", "Password"), ("lorem", "Lorem Ipsum")]),
]
TOOLS = [t for _, items in GROUPS for t in items]
SLUGS = {s for s, _ in TOOLS}
INFO = {
    "pdf_merge": "Combine several PDF files into one document.",
    "pdf_split": "Split a PDF into separate files by page range, every page, or every N pages.",
    "pdf_extract": "Pull selected pages out of a PDF into a new file, in any order.",
    "pdf_delete": "Remove selected pages from a PDF.",
    "pdf_rotate": "Rotate all or selected PDF pages by 90, 180 or 270 degrees.",
    "pdf_compress": "Reduce PDF file size with lossless optimization or JPEG image recompression.",
    "pdf_protect": "Encrypt a PDF with a password using AES-256.",
    "pdf_unlock": "Remove the password from a PDF you own.",
    "img2pdf": "Turn JPG, PNG, WebP and other images into a single PDF.",
    "pdf_info": "See a PDF's page count, page size, encryption status and metadata.",
    "cidr": "Subnet calculator for IPv4 and IPv6: network, mask, broadcast, host range and membership check.",
    "regex": "Test regular expressions against text with match highlighting and capture groups, safely sandboxed.",
    "cron": "Explain a cron expression field by field and see its next run times in UTC.",
    "currency": "Convert between 150+ currencies. Edit any amount and every other currency updates.",
    "units": "Length, weight, temperature, volume, area, speed, time, data size and pressure. Edit any field and all units update.",
    "json": "Format, minify and validate JSON. Errors show the line and column.",
    "base64": "Encode and decode Base64, UTF-8 safe, with a URL-safe option.",
    "url": "Percent-encode or decode text for URLs and query strings.",
    "jwt": "Decode a JSON Web Token's header and payload. The signature is not verified.",
    "hash": "MD5, SHA-1, SHA-256 and SHA-512 hashes of any text.",
    "uuid": "Generate random version 4 UUIDs in bulk.",
    "qr": "Turn text or a URL into a scannable QR code and download it as SVG.",
    "color": "Convert HEX, RGB and HSL and build a CSS linear gradient.",
    "time": "Convert Unix timestamps and ISO dates, seconds or milliseconds.",
    "diff": "Compare two blocks of text and see what changed, line by line.",
    "password": "Generate strong random passwords with the length and characters you choose.",
    "lorem": "Generate lorem ipsum placeholder paragraphs for layouts and mockups.",
    "case": "Convert text to camelCase, snake_case, kebab-case, Title Case and more.",
}
# slug -> (page title, textarea placeholder, [(button value, label, primary)])
SIMPLE = {
    "url": ("URL Encoder / Decoder", "Text or URL", [("encode", "Encode", 1), ("decode", "Decode", 0)], []),
    "jwt": ("JWT Decoder", "eyJhbGciOi...", [("decode", "Decode", 1)], [("secret", "HMAC secret (optional, verifies HS256/384/512)", "your-256-bit-secret")]),
    "case": ("Case Converter", "Type or paste text", [("convert", "Convert", 1)], []),
    "hash": ("Hash Generator", "Text to hash", [("hash", "Generate hashes", 1)], [("key", "HMAC key (optional)", "Leave empty for plain hashes")]),
}
