# Batch Automated Registration Tool

An automated batch registration tool with email verification and PoW security validation support.

## Project Structure

```
ohmygpt/
├── main.py                    # Main entry point, registration flow control
├── email_handler_graph.py     # Microsoft Graph API email handler module
├── ohmygpt_pow_pure.py        # Cap.js PoW solver
├── debug_security.py          # Security verification code debugging tool
├── config.example.json        # Example configuration file
├── config.json                # Actual configuration file (create manually)
└── README.md                  # Project documentation
```

## Quick Start

### 1. Install Dependencies

```bash
pip install playwright requests
playwright install chromium
```

### 2. Prepare Configuration File

Copy the example configuration file and modify it:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "referral_url": "https://www.ohmygpt.com/i/YOUR_INVITE_CODE",
  "account_file": "accounts.txt",
  "headless": false,
  "max_accounts": null,
  "delay_between_accounts": 5
}
```

**Configuration Parameters:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `referral_url` | OhMyGPT invitation link | Required |
| `account_file` | Outlook account file path | Required |
| `headless` | Run browser in headless mode (no UI) | `false` |
| `max_accounts` | Limit number of accounts to register (`null` for all) | `null` |
| `delay_between_accounts` | Delay time between accounts (seconds) | `5` |

### 3. Prepare Account File

Create an account file (e.g., `accounts.txt`), one account per line in the following format:

```
email@outlook.com----password----client_id----refresh_token
email2@outlook.com----password2----client_id2----refresh_token2
```

**Format Description:**
- Use `----` to separate fields
- `email`: Outlook email address
- `password`: Email password (optional, only for IMAP)
- `client_id`: Microsoft Azure application client ID
- `refresh_token`: Microsoft Graph API refresh token

### 4. Run the Program

```bash
python main.py -c config.json
```

## Workflow

The program automatically executes the following steps:

1. **[1/6] Visit Invitation Page** - Open the OhMyGPT invitation link
2. **[2/6] Accept Terms of Service** - Automatically check the service terms checkbox
3. **[3/6] Send Verification Email** - Enter email and request verification email
4. **[4/6] Wait for Verification Email** - Monitor email arrival via Graph API
5. **[5/6] Extract Verification Link** - Extract magic link from email
6. **[6/6] Complete Authorization** - Visit verification link and complete registration

## Core Module Description

### main.py - Main Program

Responsible for overall registration flow orchestration and browser automation.

**Main Functions:**
- `load_config()` - Load configuration file
- `register_single_account()` - Single account registration flow
- `batch_register()` - Batch registration controller

### email_handler_graph.py - Email Handler

Handles email verification using Microsoft Graph API.

**Main Class:**
```python
class OutlookGraphEmailHandler:
    def get_access_token()          # Get access token
    def search_verification_email() # Search for verification email
    def extract_verification_link() # Extract verification link
```

### ohmygpt_pow_pure.py - PoW Solver

Implements Cap.js Proof of Work verification mechanism.

**Main Class:**
```python
class CapJSPoWSolver:
    def solve()                     # Complete PoW solving process
    def solve_challenges()          # Solve multiple challenges concurrently
    def generate_challenges()       # Generate challenge list
```

**Algorithm Implementation:**
- FNV-1a hash algorithm
- Xorshift pseudo-random number generator
- Multi-threaded concurrent SHA-256 brute force

### debug_security.py - Debug Tool

Tests regular expressions for security verification code extraction. Code format is `[A-Z]\d` (e.g., A1, B6, C8).

## Security Verification Handling

The program uses three fallback methods to handle security verification codes:

1. **Method 1:** Exact match via `aria-label`
2. **Method 2:** Find input by `value` and click parent label element
3. **Method 3:** Iterate all labels to find text containing security code

## FAQ

### Q: How to obtain Microsoft Graph API client_id and refresh_token?

A: You need to register an application in [Azure Portal](https://portal.azure.com):
1. Register a new application and obtain `client_id`
2. Configure `Mail.Read` permissions
3. Obtain `refresh_token` through OAuth 2.0 authorization flow

### Q: What if the program gets stuck waiting for email?

A: Check the following:
- Is the Outlook account working properly?
- Is the refresh_token valid (may have expired)?
- Is the email being filtered to spam?
- Is the network connection stable?

### Q: What if verification code recognition fails?

A: The program tries three methods. If all fail:
- Set `headless` to `false` to manually observe the page
- Check if OhMyGPT page has been updated, causing element selectors to fail
- Use `debug_security.py` to test regular expressions

### Q: How to improve registration success rate?

A: Recommendations:
- Use a stable network environment
- Increase `delay_between_accounts` delay appropriately
- Don't use `headless` mode (some websites detect headless browsers)
- Use different invitation links to avoid rate limiting

## Important Notes

- ⚠️ This tool is for learning and research purposes only
- ⚠️ Please comply with OhMyGPT's terms of service
- ⚠️ Batch registration may violate platform rules, use with caution
- ⚠️ Set reasonable delays to avoid triggering anti-bot mechanisms
- ⚠️ Keep configuration files secure to prevent sensitive information leakage

## Development and Debugging

### View Detailed Logs

The program outputs detailed execution logs, including status and timing for each step.

### Debug Security Verification Code

```bash
python debug_security.py
```

### Run in Non-Headless Mode

Set `"headless": false` in the configuration file to view the browser automation process.

## Technical Highlights

- 🎯 Complete implementation of Cap.js PoW mechanism (FNV-1a + Xorshift PRNG)
- 🎯 Uses Microsoft Graph API instead of traditional IMAP (more stable and reliable)
- 🎯 Playwright browser automation handles complex interactions
- 🎯 Intelligent wait mechanism (up to 60 checks, 3 seconds each)
- 🎯 Multi-threaded concurrent PoW challenge solving for improved efficiency

## License

MIT License

## Disclaimer

This project is for technical research and learning purposes only. Users are responsible for any operations performed using this tool. The developer is not responsible for any consequences resulting from the use of this tool.
