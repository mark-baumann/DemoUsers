from API.TempMail import TempMail

# Create a new TempMail object
tmp = TempMail()

# If you have an API Key, use it here (you do not need an API key to use the free tier)
tmp = TempMail("tm.1234567890.randomcharactershere")

# Generate an inbox with a random domain and prefix
inb = tmp.createInbox()

# Or... use a prefix
inb = tmp.createInbox(prefix = "joe")

# Generate an inbox using a specific domain (you can also use your custom domain here)
# Prefixes on custom domains has no extra characters.  For example, a custom domain example.com
# with a prefix of "whoever" will make "whoever@example.com".  If you do not provide a prefix,
# a random one will be created for you.
inb = tmp.createInbox(domain = "mycustomdomain.com", prefix = "optional")

# Check for emails (throws exception on invalid token)
emails = tmp.getEmails(inb)

# Or... use the token (which is a string)
emails = tmp.getEmails(inb.token)

print("Emails:")

for email in emails:
    print("\tSender: " + email.sender)
    print("\tRecipient: " + email.recipient)
    print("\tSubject: " + email.subject)
    print("\tBody: " + email.body)
    print("\tHTML: " + str(email.html)) # may be None
    print("\tDate: " + str(email.date)) # Unix timestamp in milliseconds