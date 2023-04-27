import requests
import json
import time
import asyncio
import websockets
import discord
from discord.ext import commands, tasks
from web3 import Web3
from web3.middleware import geth_poa_middleware

PEPE_ADDRESS = "0xA43fe16908251ee70EF74718545e4FE6C5cCEc9f"
APP_TOKEN = "YOUR_APP_TOKEN"
NODE_ENDPOINT = "YOUR_NODE_ENDPOINT"


w3 = Web3(Web3.HTTPProvider(NODE_ENDPOINT))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)


class MyClient(discord.Client):
    def truncate_string(self, string, length=10):
        if len(string) <= length:
            return string
        else:
            return string[:6] + ".." + string[-3:]

    def eth_to_usd(self, eth_amount):
        # Make a request to the CoinGecko API to get the current ETH price in USD
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')

        # Extract the ETH price from the response
        eth_price = response.json()['ethereum']['usd']

        # Calculate the value of the ETH amount in USD
        eth_usd_value = eth_amount * float(eth_price)

        # Return the value of the ETH amount in USD
        return eth_usd_value

    async def on_ready(self):
        print("Bot is ready")
        await self.subscribe_to_transfers()

    async def handle_event(self, event):
        hexdata = event['data']
        hexdataTrimed = hexdata[2:]
        # Split trimmed string every 64 characters
        n = 64
        dataSplit = [hexdataTrimed[i:i + n] for i in range(0, len(hexdataTrimed), n)]
        # Fill new list with converted decimal values
        data = []
        for val in range(len(dataSplit)):
            toDec = int(dataSplit[val], 16)
            data.append(toDec)
        data = list(filter(lambda x: x != 0, data))
        tokenOut = data[0]
        tokenIn = data[1]
        eth_amount = w3.from_wei(tokenOut, 'ether')
        pepe_amount = w3.from_wei(tokenIn, 'ether')
        if tokenOut < tokenIn and float(eth_amount) > 0.09:
            activity = 'buy'

            tx = w3.eth.get_transaction(event['transactionHash'])
            eth_usd_amount = self.eth_to_usd(float(eth_amount))
            print(f"{eth_amount}", f"{pepe_amount:,.0f}", activity, event['transactionHash'], tx['from'])
            num_frogs = int(eth_amount * 50)  # Scale the number of frogs based on the eth_amount

            # Create the frog emoji string by repeating the 🐸 emoji `num_frogs` times
            frog_emoji = "🐸" * num_frogs
            embed = discord.Embed(title=f"$PEPE {activity.upper()}!", description=frog_emoji, color=0x00ff00)
            # embed.set_thumbnail(url="https://i.4cdn.org/r9k/1682023274432244.jpg")
            embed.set_image(url="https://i.4cdn.org/r9k/1682023274432244.jpg")
            embed.add_field(name=f"️", value=f"", inline=False)
            embed.add_field(name=f"{eth_amount:.8f} ETH ({eth_usd_amount:,.2f} USD) ➡️", value=f"{pepe_amount:,.0f} PEPE", inline=False)
            embed.add_field(name=f"", value=f"🪪 [{self.truncate_string(tx['from'])}](https://etherscan.com/address/{tx['from']}) | [Txn](https://etherscan.com/tx/{event['transactionHash']})\n 📊 [Chart](https://www.dextools.io/app/en/ether/pair-explorer/0xa43fe16908251ee70ef74718545e4fe6c5ccec9f)", inline=False)

            for guild in client.guilds:
                # Find the "general" channel in the guild
                channel = discord.utils.get(guild.channels, name="buys")
                if channel:
                    # Send the embed message to the "general" channel
                    await channel.send(embed=embed)
        else:
            activity = 'sell'
            pepe_amount = w3.from_wei(tokenOut, 'ether')
            eth_amount = w3.from_wei(tokenIn, 'ether')

            tx = w3.eth.get_transaction(event['transactionHash'])
            eth_usd_amount = self.eth_to_usd(float(eth_amount))
            print(f"{eth_amount}", f"{pepe_amount:,.0f}", activity, event['transactionHash'], tx['from'])
            num_frogs = int(eth_amount * 50)  # Scale the number of frogs based on the eth_amount

            # Create the frog emoji string by repeating the 🐸 emoji `num_frogs` times
            frog_emoji = "🐸" * num_frogs
            embed = discord.Embed(title=f"$PEPE {activity.upper()}!", description=frog_emoji, color=0xFF0000)
            embed.set_thumbnail(url="https://i.4cdn.org/r9k/1682023274432244.jpg")
            # embed.set_image(url="https://i.4cdn.org/r9k/1682023274432244.jpg")
            embed.add_field(name=f"️", value=f"", inline=False)
            embed.add_field(name=f"{eth_amount:.8f} ETH ({eth_usd_amount:,.2f} USD) ➡️",
                            value=f"{pepe_amount:,.0f} PEPE", inline=False)
            embed.add_field(name=f"",
                            value=f"🪪 [{self.truncate_string(tx['from'])}](https://etherscan.com/address/{tx['from']}) | [Txn](https://etherscan.com/tx/{event['transactionHash']})\n 📊 [Chart](https://www.dextools.io/app/en/ether/pair-explorer/0xa43fe16908251ee70ef74718545e4fe6c5ccec9f)",
                            inline=False)

            for guild in client.guilds:
                # Find the "general" channel in the guild
                channel = discord.utils.get(guild.channels, name="sales")
                if channel:
                    # Send the embed message to the "general" channel
                    await channel.send(embed=embed)


    async def subscribe_to_transfers(self):
        async with websockets.connect(f'wss://{NODE_ENDPOINT[8:]}') as websocket:
            # subscribe to the Transfer event for the PEPE token
            subscription_id = await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": PEPE_ADDRESS,
                        "topics": [
                            "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
                        ]
                    }
                ],
                "id": 1
            }))

            while True:
                response = await websocket.recv()
                response = json.loads(response)
                try:
                    await self.handle_event(response['params']['result'])
                except Exception as e:
                    print(e)


intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(APP_TOKEN)
