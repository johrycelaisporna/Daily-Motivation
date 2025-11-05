name: Contract Expiration Alerts

on:
  schedule:
    # Runs every Monday at 6:00 AM Manila time (10:00 PM UTC previous day)
    - cron: '0 22 * * 0'
  workflow_dispatch: # Allows manual trigger for testing

jobs:
  check-contracts:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Run contract expiration bot
      env:
        MONDAY_API_TOKEN: ${{ secrets.MONDAY_API_TOKEN }}
        SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
      run: |
        python contract_expiration_bot.py
