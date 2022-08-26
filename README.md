# Account Service

The Account Service has the following endpoints:

1. Netwrok:
    
   Support blockchain networks to connect wallet.

2. Wallet:

    Connected wallet address

3. Accounts:

    Accounts (sub accounts) created for each connected wallet.

4. Crypto:

    Tokens can be deposit and withdraw from exchange.

5. Balance:

    Each account balance

6. Order:

    Send and cancel order

7. Trade:

    Trades created by each account orders.
    

# Execution

In the project directory you have the following options:

* Python:
    
    1. Install the requirments.txt file:

        ```
        pip install -r requirements.txt
        ```

    2.  Run the following command:

        ```
        python app/main.py
        ```

* Docker:

    Run the following command:
    ```
    docker-compose up
    ```
    or 
    ```
    docker-compose up -d 
    ```
    to run in detach mode.