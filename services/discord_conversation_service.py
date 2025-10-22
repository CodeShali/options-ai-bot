"""
Discord Conversational AI Service
Natural language interface for trading system queries and assistance.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
import discord
from discord import ui

from services import (
    get_alpaca_service,
    get_database_service,
    get_cache_service,
    get_llm_service,
)
from .discord_nlp_core import is_trading_related, extract_symbols, classify_intent


class ReactionConfirmation:
    """Reaction-based confirmation for NLP actions."""
    
    def __init__(self, action_data: Dict[str, Any], conversation_service, user_id: int, message):
        self.action_data = action_data
        self.conversation_service = conversation_service
        self.user_id = user_id
        self.message = message
        self.confirmed = None
        
    async def setup_reactions(self):
        """Add reaction emojis for confirmation."""
        await self.message.add_reaction("✅")  # Confirm
        await self.message.add_reaction("❌")  # Cancel
        
    async def handle_reaction(self, reaction, user):
        """Handle reaction from user."""
        if user.id != self.user_id:
            return False
            
        if str(reaction.emoji) == "✅":
            # Execute the action
            result = await self.conversation_service._execute_function(self.action_data)
            
            # Send result as reply
            if result.get("success"):
                results_text = "\n".join(result.get("results", [result.get("message", "Done!")]))
                await self.message.reply(f"✅ **Action Completed:**\n{results_text}")
                
                # Send trade summary if it was a trade
                await self._send_trade_summary(result)
            else:
                await self.message.reply(f"❌ **Error:** {result.get('error', 'Unknown error')}")
            
            # Clear reactions
            await self.message.clear_reactions()
            return True
            
        elif str(reaction.emoji) == "❌":
            await self.message.reply("❌ Action cancelled.")
            await self.message.clear_reactions()
            return True
            
        return False
    
    async def _send_trade_summary(self, result):
        """Send a summary update after trade execution."""
        try:
            # Get updated account and position info
            alpaca = self.conversation_service.alpaca
            account = await alpaca.get_account()
            
            summary = f"📊 **Trade Summary Update**\n\n"
            summary += f"💰 **Account:** ${float(account.get('equity', 0)):,.2f} equity\n"
            summary += f"💵 **Buying Power:** ${float(account.get('buying_power', 0)):,.2f}\n\n"
            
            # If it was a sell, show P&L impact
            if 'sell' in result.get('message', '').lower():
                symbol = result.get('symbol', 'N/A')
                try:
                    # Try to get position (might be gone if fully sold)
                    position = await alpaca.get_position(symbol)
                    if position:
                        summary += f"📈 **{symbol} Position:** {position.get('qty', 0)} shares remaining\n"
                        summary += f"💹 **Unrealized P&L:** ${float(position.get('unrealized_pl', 0)):+,.2f}\n"
                    else:
                        summary += f"✅ **{symbol} Position:** Fully closed\n"
                except:
                    pass
            
            await self.message.channel.send(summary)
            
        except Exception as e:
            logger.error(f"Error sending trade summary: {e}")


# Legacy view for backward compatibility
class ConfirmationView(ui.View):
    """Interactive confirmation buttons for NLP actions (legacy)."""
    
    def __init__(self, action_data: Dict[str, Any], conversation_service, user_id: int):
        super().__init__(timeout=60)
        self.action_data = action_data
        self.conversation_service = conversation_service
        self.user_id = user_id
        self.confirmed = None
    
    @ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        """Confirm the action."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
            return
        
        await interaction.response.defer()
        self.confirmed = True
        self.stop()
        
        # Execute the action
        result = await self.conversation_service._execute_function(self.action_data)
        
        # Send result
        if result.get("success"):
            results_text = "\n".join(result.get("results", [result.get("message", "Done!")]))
            await interaction.followup.send(f"✅ **Action Completed:**\n{results_text}")
        else:
            await interaction.followup.send(f"❌ **Error:** {result.get('error', 'Unknown error')}")
    
    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel the action."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
            return
        
        await interaction.response.send_message("❌ Action cancelled.", ephemeral=False)
        self.confirmed = False
        self.stop()


class DiscordConversationService:
    """Natural language conversation interface for Discord with session management."""

    def __init__(self, bot):
        self.bot = bot
        self.alpaca = get_alpaca_service()
        self.db = get_database_service()
        self.cache = get_cache_service()
        self.llm = get_llm_service()
        # Orchestrator (if running full system via main.py)
        self.orchestrator = getattr(bot, 'orchestrator', None)
        self.enabled = True
        
        # Session management: Store conversation history per user
        # Format: {user_id: [{"role": "user/assistant", "content": "...", "timestamp": datetime}, ...]}
        self.sessions: Dict[int, List[Dict[str, Any]]] = {}
        self.max_history_per_user = 10  # Keep last 10 messages per user
        self.session_timeout_minutes = 30  # Clear session after 30 min of inactivity
        
        logger.info("💬 Conversation service ready with session management")

    async def handle_message(self, message: discord.Message) -> Optional[str]:
        """Return a response string if we should respond, else None. Maintains conversation history."""
        try:
            if not self.enabled:
                return None
            if message.author.bot:
                return None
            content = (message.content or "").strip()
            if not content:
                return None
            if content.startswith('/'):
                return None

            # Only respond to trading-related messages
            if not is_trading_related(content):
                # Polite redirect for off-topic
                return (
                    "I'm focused on trading and your portfolio. "
                    "Ask me about your account, positions, risk, alerts, or strategy and I'll help. 📊"
                )

            user_id = message.author.id
            
            # Clean up old sessions
            self._cleanup_old_sessions()
            
            # Get or create session for this user
            if user_id not in self.sessions:
                self.sessions[user_id] = []
            
            # Build facts/context from live data with cache-first strategy
            facts = await self._gather_top_facts(content)
            system = self._build_system_prompt()
            user_prompt = self._build_user_prompt(content, facts)

            # Build messages array with conversation history
            messages = [{"role": "system", "content": system}]
            
            # Add recent conversation history (last 6 messages = 3 exchanges)
            recent_history = self.sessions[user_id][-6:] if self.sessions[user_id] else []
            for hist in recent_history:
                messages.append({
                    "role": hist["role"],
                    "content": hist["content"]
                })
            
            # Add current user message
            messages.append({"role": "user", "content": user_prompt})

            # Define available functions for the AI
            functions = self._get_available_functions()

            reply = await self.llm.chat_completion(
                messages=messages,
                temperature=0.4,
                max_tokens=550,
                model="gpt-4o-mini",
                functions=functions,
                function_call="auto"
            )
            
            # Check if AI wants to call a function
            if isinstance(reply, dict) and "function_call" in reply:
                # Handle function calling
                function_name = reply["function_call"]["name"]
                import json
                arguments = json.loads(reply["function_call"]["arguments"])
                
                # Store the function call for confirmation
                function_call_data = {
                    "name": function_name,
                    "arguments": arguments
                }
                
                # Create confirmation message
                if function_name == "set_stop_loss":
                    symbols = arguments.get("symbols", [])
                    pct = arguments.get("stop_loss_pct", 0)
                    confirmation_msg = (
                        f"📊 **Confirm Stop-Loss Order**\n\n"
                        f"I will set **-{pct}% stop-loss** for:\n"
                        + "\n".join([f"• {sym}" for sym in symbols]) +
                        f"\n\n**Click ✅ Confirm to execute**"
                    )
                elif function_name == "modify_stop_loss":
                    symbols = arguments.get("symbols", [])
                    pct = arguments.get("stop_loss_pct", 0)
                    confirmation_msg = (
                        f"🛠️ **Confirm Modify Stop-Loss**\n\n"
                        f"I will replace existing stop-loss with **-{pct}%** for:\n"
                        + "\n".join([f"• {sym}" for sym in symbols]) +
                        f"\n\nExisting stop orders (if any) will be cancelled.\n\n**Click ✅ Confirm to execute**"
                    )
                elif function_name == "set_take_profit":
                    symbols = arguments.get("symbols", [])
                    pct = arguments.get("take_profit_pct", 0)
                    confirmation_msg = (
                        f"🎯 **Confirm Take-Profit Order**\n\n"
                        f"I will set **+{pct}% take-profit** for:\n"
                        + "\n".join([f"• {sym}" for sym in symbols]) +
                        f"\n\n**React ✅ to confirm or ❌ to cancel**"
                    )
                elif function_name == "cancel_symbol_orders":
                    symbol = arguments.get("symbol", "")
                    confirmation_msg = (
                        f"🚫 **Confirm Cancel Orders**\n\n"
                        f"I will cancel all open orders for **{symbol}**.\n\n"
                        f"**React ✅ to confirm or ❌ to cancel**"
                    )
                elif function_name == "place_order":
                    symbol = arguments.get("symbol", "")
                    qty = arguments.get("qty", 0)
                    side = arguments.get("side", "buy")
                    order_type = arguments.get("order_type", "market")
                    price_text = ""
                    if order_type == "limit" and arguments.get("limit_price"):
                        price_text = f" @ ${arguments['limit_price']:.2f}"
                    confirmation_msg = (
                        f"🛒 **Confirm Order**\n\n"
                        f"{side.upper()} {qty} {symbol} — {order_type.upper()}{price_text}\n\n"
                        f"**React ✅ to confirm or ❌ to cancel**"
                    )
                elif function_name == "sell_position":
                    symbol = arguments.get("symbol", "")
                    confirmation_msg = (
                        f"💼 **Confirm Sell Order**\n\n"
                        f"I will **sell your entire {symbol} position**.\n\n"
                        f"*Note: If shares are held by open orders, I'll cancel those first.*\n\n"
                        f"**React ✅ to confirm or ❌ to cancel**"
                    )
                else:
                    confirmation_msg = f"Confirm action: {function_name}\n\n**React ✅ to confirm or ❌ to cancel**"
                
                # Store pending action and return confirmation with reactions
                self.sessions[user_id].append({
                    "role": "assistant",
                    "content": confirmation_msg,
                    "timestamp": datetime.now(),
                    "pending_action": function_call_data
                })
                
                reply = {
                    "content": confirmation_msg,
                    "needs_reaction_confirmation": True,
                    "action_data": function_call_data,
                    "user_id": user_id
                }
            else:
                # Regular conversational response - ALWAYS add reaction emojis
                reply_content = reply if isinstance(reply, str) else str(reply)
                reply = {
                    "content": reply_content,
                    "needs_reactions": True,  # Add reactions to ALL responses
                    "user_id": user_id
                }
            
            # Store in session history (only if not a confirmation request)
            if not isinstance(reply, dict) or (not reply.get("needs_confirmation") and not reply.get("needs_reaction_confirmation")):
                now = datetime.now()
                self.sessions[user_id].append({
                    "role": "user",
                    "content": content,  # Store original user message
                    "timestamp": now
                })
                self.sessions[user_id].append({
                    "role": "assistant",
                    "content": str(reply) if not isinstance(reply, dict) else reply.get("content", ""),
                    "timestamp": now
                })
                
                # Trim history if too long
                if len(self.sessions[user_id]) > self.max_history_per_user * 2:  # *2 for user+assistant pairs
                    self.sessions[user_id] = self.sessions[user_id][-(self.max_history_per_user * 2):]
            
            return reply
        except Exception as e:
            logger.error(f"Conversation error: {e}")
            return "I hit an error answering that. Please try again or use a slash command."
    
    def _cleanup_old_sessions(self):
        """Remove sessions that haven't been active for a while."""
        from datetime import timedelta
        now = datetime.now()
        timeout = timedelta(minutes=self.session_timeout_minutes)
        
        users_to_remove = []
        for user_id, history in self.sessions.items():
            if history:
                last_message_time = history[-1].get("timestamp", now)
                if now - last_message_time > timeout:
                    users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.sessions[user_id]
            logger.debug(f"Cleared inactive session for user {user_id}")

    async def _gather_top_facts(self, content: str) -> Dict[str, Any]:
        """Collect lightweight, cache-first facts to ground the answer."""
        facts: Dict[str, Any] = {"now": datetime.now().strftime('%b %d, %Y %I:%M %p ET')}
        symbols = extract_symbols(content)
        facts["symbols"] = symbols

        # Account (cache-first)
        acct = await self.cache.get("account")
        if not acct:
            try:
                acct = await self.alpaca.get_account()
                await self.cache.set("account", acct, ttl=60)
            except Exception:
                acct = {"equity": "N/A", "buying_power": "N/A", "cash": "N/A", "portfolio_value": "N/A"}
        facts["account"] = {
            "equity": float(acct.get("equity", 0)) if str(acct.get("equity", "0")).replace('.', '', 1).isdigit() else acct.get("equity", "N/A"),
            "buying_power": acct.get("buying_power", "N/A"),
            "cash": acct.get("cash", "N/A"),
            "portfolio_value": acct.get("portfolio_value", "N/A"),
        }

        # Positions (cache-first, fall back to DB)
        positions = await self.cache.get("positions")
        if positions is None:
            try:
                positions = await self.alpaca.get_positions()
                await self.cache.set("positions", positions, ttl=30)
            except Exception:
                try:
                    positions = await self.db.get_open_positions()
                except Exception:
                    positions = []
        facts["positions"] = self._minify_positions(positions)

        # Recent trades (DB)
        try:
            trades = await self.db.get_recent_trades(10)
        except Exception:
            trades = []
        facts["recent_trades"] = self._minify_trades(trades)

        # Intent
        facts["intent"] = classify_intent(content)
        return facts

    def _minify_positions(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for p in positions[:10]:
            try:
                out.append({
                    "symbol": p.get("symbol"),
                    "qty": int(float(p.get("qty", 0))),
                    "entry": float(p.get("avg_entry_price", 0) or p.get("avg_entry", 0) or 0),
                    "price": float(p.get("current_price", 0) or 0),
                    "upl": float(p.get("unrealized_pl", 0) or 0),
                    "upl_pct": float(p.get("unrealized_plpc", 0) or 0) * 100,
                })
            except Exception:
                continue
        return out

    def _minify_trades(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for t in trades[:5]:
            out.append({
                "symbol": t.get("symbol"),
                "action": t.get("action"),
                "qty": t.get("quantity"),
                "price": t.get("price"),
                "timestamp": t.get("timestamp"),
            })
        return out

    def _build_system_prompt(self) -> str:
        return (
            "You are TARA, an intelligent trading assistant with a conversational, helpful personality. "
            "You're like ChatGPT but specialized for trading and portfolio management. "
            "\n\n**PERSONALITY:**"
            "\n- Be conversational, friendly, and helpful like ChatGPT"
            "\n- Explain things clearly and ask follow-up questions when needed"
            "\n- Use natural language, not robotic responses"
            "\n- Show enthusiasm for helping with trading decisions"
            "\n- Use emojis naturally: 📊 📈 📉 🎯 💰 ⚠️ ✅ 🤔 💡"
            "\n\n**CAPABILITIES:**"
            "\n- Answer questions about account, positions, market analysis"
            "\n- Execute trades: set stop losses, take profits, buy/sell stocks"
            "\n- Provide personalized trading advice based on current portfolio"
            "\n- Explain market movements and trading strategies"
            "\n\n**EXECUTION RULES:**"
            "\n- When user wants to trade, use the appropriate function (set_stop_loss, place_order, etc.)"
            "\n- Always confirm before executing trades with clear details"
            "\n- Use real account data provided in context - never make up numbers"
            "\n- If user asks 'should I buy X?', analyze their portfolio and give personalized advice"
            "\n\n**CONVERSATION STYLE:**"
            "\n- Ask clarifying questions: 'Which positions?' 'What percentage?' 'Market or limit order?'"
            "\n- Provide context: 'Based on your current AAPL position...' 'Looking at your portfolio...'"
            "\n- Be proactive: 'I notice you don't have stop losses set. Would you like me to add them?'"
            "\n- Keep responses conversational but informative (2-6 sentences typically)"
        )

    def _get_available_functions(self) -> List[Dict[str, Any]]:
        """Define functions that the AI can call."""
        return [
            {
                "name": "set_stop_loss",
                "description": "Set stop-loss orders for one or more positions at a specific percentage below current price",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of stock symbols to set stop loss for (e.g., ['AAPL', 'TSLA'])"
                        },
                        "stop_loss_pct": {
                            "type": "number",
                            "description": "Stop loss percentage (e.g., 2 for -2%)"
                        }
                    },
                    "required": ["symbols", "stop_loss_pct"]
                }
            },
            {
                "name": "place_order",
                "description": "Place a stock order (buy/sell) with market or limit type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "side": {"type": "string", "enum": ["buy", "sell"]},
                        "qty": {"type": "integer", "minimum": 1},
                        "order_type": {"type": "string", "enum": ["market", "limit"]},
                        "limit_price": {"type": "number"},
                        "time_in_force": {"type": "string", "default": "day"}
                    },
                    "required": ["symbol", "side", "qty", "order_type"]
                }
            },
            {
                "name": "modify_stop_loss",
                "description": "Modify (replace) existing stop-loss for one or more symbols to a new percentage",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "stop_loss_pct": {"type": "number"}
                    },
                    "required": ["symbols", "stop_loss_pct"]
                }
            },
            {
                "name": "set_take_profit",
                "description": "Place take-profit (limit) orders for positions using a percent above current price",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "take_profit_pct": {"type": "number"}
                    },
                    "required": ["symbols", "take_profit_pct"]
                }
            },
            {
                "name": "cancel_symbol_orders",
                "description": "Cancel open orders for a symbol (optionally filter by type)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "order_type": {"type": "string", "description": "Optional: market, limit, stop"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "sell_position",
                "description": "Sell/close a position completely",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol to sell (e.g., 'AAPL')"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_position_details",
                "description": "Get detailed information about a specific position",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol (e.g., 'AAPL')"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "buy_stock",
                "description": "Buy shares of a stock with AI analysis and recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol to buy (e.g., 'AAPL')"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Number of shares to buy (optional, will suggest if not provided)",
                            "minimum": 1
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "buy_option",
                "description": "Find and buy best options contracts with Greeks analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol for options (e.g., 'AAPL')"
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["call", "put"],
                            "description": "Option strategy: 'call' for bullish, 'put' for bearish"
                        },
                        "max_risk": {
                            "type": "number",
                            "description": "Maximum risk per contract in dollars (default: 1000)",
                            "default": 1000
                        }
                    },
                    "required": ["symbol", "strategy"]
                }
            }
        ]
    
    async def _execute_function(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function called by the AI."""
        import json
        
        function_name = function_call.get("name")
        arguments = json.loads(function_call.get("arguments", "{}"))
        
        logger.info(f"🤖 AI calling function: {function_name} with args: {arguments}")
        
        try:
            if function_name == "set_stop_loss":
                return await self._set_stop_loss(arguments)
            elif function_name == "place_order":
                return await self._place_order(arguments)
            elif function_name == "modify_stop_loss":
                return await self._modify_stop_loss(arguments)
            elif function_name == "set_take_profit":
                return await self._set_take_profit(arguments)
            elif function_name == "cancel_symbol_orders":
                return await self._cancel_symbol_orders(arguments)
            elif function_name == "sell_position":
                return await self._sell_position(arguments)
            elif function_name == "get_position_details":
                return await self._get_position_details(arguments)
            elif function_name == "buy_stock":
                return await self._buy_stock(arguments)
            elif function_name == "buy_option":
                return await self._buy_option(arguments)
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {"error": str(e)}
    
    async def _set_stop_loss(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Set stop-loss orders for positions."""
        symbols = args.get("symbols", [])
        stop_loss_pct = args.get("stop_loss_pct", 0)
        
        # Prefer execution agent if orchestrator is available
        if self.orchestrator and getattr(self.orchestrator, 'execution', None):
            return await self.orchestrator.execution.set_stop_losses(symbols, stop_loss_pct)
        
        # Fallback: direct Alpaca
        results = []
        for symbol in symbols:
            try:
                position = await self.alpaca.get_position(symbol)
                if not position:
                    results.append(f"{symbol}: No position found")
                    continue
                current_price = float(position.get("current_price", 0))
                qty = float(position.get("qty", 0))
                stop_price = current_price * (1 - stop_loss_pct / 100)
                order = await self.alpaca.place_order(
                    symbol=symbol,
                    qty=int(abs(qty)),
                    side="sell",
                    order_type="stop",
                    stop_price=round(stop_price, 2)
                )
                results.append(f"✅ {symbol}: Stop-loss set at ${stop_price:.2f} (order ID: {order.get('id', 'N/A')})")
            except Exception as e:
                results.append(f"❌ {symbol}: Error - {str(e)}")
        return {"success": True, "results": results}

    async def _place_order(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Place a stock order using Alpaca service wrapper."""
        try:
            symbol = args.get("symbol", "").upper()
            side = (args.get("side") or "").lower()
            qty = int(args.get("qty", 0))
            order_type = (args.get("order_type") or "market").lower()
            time_in_force = (args.get("time_in_force") or "day").lower()
            limit_price = args.get("limit_price")
            if order_type == "limit" and limit_price is None:
                return {"error": "limit_price is required for limit orders"}
            # Prefer execution agent for buys/sells
            if self.orchestrator and getattr(self.orchestrator, 'execution', None):
                if side == "buy":
                    trade = {"symbol": symbol, "quantity": qty, "price": float(limit_price) if limit_price else 0.0}
                    res = await self.orchestrator.execution.execute_buy(trade)
                else:
                    res = await self.orchestrator.execution.execute_sell(symbol, qty, reason="NLP place_order")
                if res.get("success"):
                    return {"success": True, "message": res.get("message") or "✅ Order submitted", "order": res}
                return {"error": res.get("error", "Order failed")}
            
            # Fallback: direct Alpaca
            order = await self.alpaca.place_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type=order_type,
                limit_price=limit_price,
                time_in_force=time_in_force,
            )
            return {"success": True, "message": f"✅ Order submitted: {side.upper()} {qty} {symbol} ({order_type.upper()}) — ID {order.get('id','N/A')}", "order": order}
        except Exception as e:
            return {"error": str(e)}

    async def _modify_stop_loss(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Replace existing stop-loss orders with a new percentage."""
        symbols = args.get("symbols", [])
        stop_loss_pct = args.get("stop_loss_pct", 0)
        # Use execution agent by cancelling and setting new stops
        if self.orchestrator and getattr(self.orchestrator, 'execution', None):
            # Cancel stops then set new ones
            for sym in symbols:
                try:
                    await self.orchestrator.execution.cancel_open_orders_for_symbol(sym, order_type="stop")
                except Exception:
                    pass
            return await self.orchestrator.execution.set_stop_losses(symbols, stop_loss_pct)
        
        # Fallback: direct approach via Alpaca
        results = []
        try:
            open_orders = await self.alpaca.get_orders(status="open", limit=100)
        except Exception:
            open_orders = []
        for symbol in symbols:
            try:
                cancelled = 0
                for o in open_orders:
                    if o.get("symbol") == symbol and (o.get("type") in ["stop", "stop_limit"]):
                        if await self.alpaca.cancel_order(o.get("id")):
                            cancelled += 1
                position = await self.alpaca.get_position(symbol)
                if not position:
                    results.append(f"{symbol}: No position found")
                    continue
                current_price = float(position.get("current_price", 0))
                qty = int(abs(float(position.get("qty", 0))))
                stop_price = round(current_price * (1 - stop_loss_pct / 100), 2)
                await self.alpaca.place_order(
                    symbol=symbol, qty=int(qty), side="sell", order_type="stop", stop_price=stop_price, time_in_force="gtc"
                )
                results.append(f"✅ {symbol}: Replaced stop-loss at ${stop_price:.2f} (cancelled {cancelled})")
            except Exception as e:
                results.append(f"❌ {symbol}: Error - {str(e)}")
        return {"success": True, "results": results}

    async def _set_take_profit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Place take-profit limit orders at percentage above current price."""
        symbols = args.get("symbols", [])
        tp_pct = args.get("take_profit_pct", 0)
        if self.orchestrator and getattr(self.orchestrator, 'execution', None):
            return await self.orchestrator.execution.set_take_profits(symbols, tp_pct)
        results = []
        for symbol in symbols:
            try:
                position = await self.alpaca.get_position(symbol)
                if not position:
                    results.append(f"{symbol}: No position found")
                    continue
                current_price = float(position.get("current_price", 0))
                qty = abs(float(position.get("qty", 0)))
                limit_price = round(current_price * (1 + tp_pct / 100), 2)
                await self.alpaca.place_order(
                    symbol=symbol, qty=int(qty), side="sell", order_type="limit", limit_price=limit_price, time_in_force="gtc"
                )
                results.append(f"✅ {symbol}: Take-profit placed at ${limit_price:.2f}")
            except Exception as e:
                results.append(f"❌ {symbol}: Error - {str(e)}")
        return {"success": True, "results": results}

    async def _cancel_symbol_orders(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel open orders for symbol, optionally filtered by type."""
        symbol = args.get("symbol", "").upper()
        order_type = (args.get("order_type") or "").lower().strip() or None
        # Prefer execution agent when available
        if self.orchestrator and getattr(self.orchestrator, 'execution', None):
            result = await self.orchestrator.execution.cancel_open_orders_for_symbol(symbol, order_type)
            if result.get("success"):
                return {"success": True, "message": f"Cancelled {result.get('cancelled',0)} open order(s) for {symbol}"}
            return {"error": result.get("error", "Failed to cancel orders")}
        
        # Fallback: direct Alpaca
        try:
            orders = await self.alpaca.get_orders(status="open", limit=200)
        except Exception as e:
            return {"error": f"Failed to fetch open orders: {e}"}
        cancelled = 0
        for o in orders:
            if o.get("symbol") != symbol:
                continue
            if order_type and (o.get("type") != order_type):
                continue
            try:
                if await self.alpaca.cancel_order(o.get("id")):
                    cancelled += 1
            except Exception:
                continue
        return {"success": True, "message": f"Cancelled {cancelled} open order(s) for {symbol}"}
    
    async def _sell_position(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sell a position."""
        symbol = args.get("symbol", "").upper()
        
        try:
            # Prefer execution agent
            if self.orchestrator and getattr(self.orchestrator, 'execution', None):
                # First, try to cancel any existing sell orders for this symbol
                try:
                    cancel_result = await self.orchestrator.execution.cancel_open_orders_for_symbol(symbol, order_type="sell")
                    if cancel_result.get("cancelled", 0) > 0:
                        logger.info(f"Cancelled {cancel_result['cancelled']} existing sell orders for {symbol}")
                except Exception as e:
                    logger.warning(f"Could not cancel existing orders for {symbol}: {e}")
                
                # Now try to sell all available shares
                res = await self.orchestrator.execution.execute_sell(symbol, None, reason="NLP sell_position")
                if res.get("success"):
                    qty = res.get("quantity") or 0
                    return {"success": True, "message": f"✅ Sold {qty} shares of {symbol}"}
                
                # If still failing due to held shares, provide helpful error
                error_msg = res.get("error", "Sell failed")
                if "held by orders" in error_msg.lower():
                    return {"error": f"❌ Cannot sell {symbol}: shares are tied up in other orders. Try canceling all orders for {symbol} first, then sell."}
                return {"error": error_msg}
            
            # Fallback: direct Alpaca
            position = await self.alpaca.get_position(symbol)
            if not position:
                return {"error": f"No position found for {symbol}"}
            qty = int(abs(float(position.get("qty", 0))))
            order = await self.alpaca.place_order(
                symbol=symbol,
                qty=qty,
                side="sell",
                order_type="market"
            )
            return {"success": True, "message": f"✅ Sold {qty} shares of {symbol} (order ID: {order.get('id', 'N/A')})"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_position_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed position information."""
        symbol = args.get("symbol", "").upper()
        
        try:
            position = await self.alpaca.get_position(symbol)
            if not position:
                return {"error": f"No position found for {symbol}"}
            
            return {
                "symbol": symbol,
                "qty": position.get("qty"),
                "entry_price": position.get("avg_entry_price"),
                "current_price": position.get("current_price"),
                "unrealized_pl": position.get("unrealized_pl"),
                "unrealized_plpc": position.get("unrealized_plpc")
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _buy_stock(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Buy stock with AI analysis."""
        from services.buy_assistant_service import get_buy_assistant_service
        
        symbol = args.get("symbol", "").upper()
        quantity = args.get("quantity")
        
        try:
            buy_assistant = get_buy_assistant_service()
            
            # Analyze the opportunity
            analysis = await buy_assistant.analyze_buy_opportunity(symbol)
            
            if "error" in analysis:
                return {"error": analysis["error"]}
            
            current_price = analysis["current_price"]
            buying_power = analysis["buying_power"]
            max_shares = analysis["max_shares"]
            
            # If no quantity, suggest 5% of buying power
            if quantity is None:
                suggested_value = buying_power * 0.05
                quantity = int(suggested_value / current_price)
                quantity = max(1, min(quantity, max_shares))
            
            estimated_cost = current_price * quantity
            
            if estimated_cost > buying_power:
                return {
                    "error": f"Insufficient buying power. Need ${estimated_cost:,.2f}, have ${buying_power:,.2f}. Max shares: {max_shares}"
                }
            
            return {
                "success": True,
                "symbol": symbol,
                "quantity": quantity,
                "current_price": current_price,
                "estimated_cost": estimated_cost,
                "buying_power_after": buying_power - estimated_cost,
                "message": f"Ready to buy {quantity} shares of {symbol} at ~${current_price:.2f} (Total: ${estimated_cost:,.2f})"
            }
            
        except Exception as e:
            logger.error(f"Error in buy_stock: {e}")
            return {"error": str(e)}
    
    async def _buy_option(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find and recommend best options."""
        from services.buy_assistant_service import get_buy_assistant_service
        
        symbol = args.get("symbol", "").upper()
        strategy = args.get("strategy", "call").lower()
        max_risk = args.get("max_risk", 1000.0)
        
        try:
            buy_assistant = get_buy_assistant_service()
            
            # Find best options
            best_options = await buy_assistant.find_best_options(
                symbol=symbol,
                strategy=strategy,
                max_risk=max_risk,
                target_delta=0.5
            )
            
            if not best_options:
                return {
                    "error": f"No suitable {strategy} options found for {symbol} within ${max_risk:,.2f} risk"
                }
            
            # Return top 3 options
            recommendations = []
            for i, opt in enumerate(best_options[:3], 1):
                recommendations.append({
                    "rank": i,
                    "symbol": opt["symbol"],
                    "strike": opt["strike"],
                    "expiration": opt["expiration"],
                    "days_to_exp": opt["days_to_exp"],
                    "cost": opt["contract_cost"],
                    "delta": opt["delta"],
                    "risk_level": opt["risk_level"],
                    "score": opt["score"],
                    "recommendation": opt["recommendation"]
                })
            
            return {
                "success": True,
                "symbol": symbol,
                "strategy": strategy,
                "options_found": len(best_options),
                "top_recommendations": recommendations,
                "message": f"Found {len(best_options)} {strategy} options for {symbol}. Top recommendation: {recommendations[0]['symbol']} at ${recommendations[0]['cost']:.2f}"
            }
            
        except Exception as e:
            logger.error(f"Error in buy_option: {e}")
            return {"error": str(e)}
    
    def _build_user_prompt(self, content: str, facts: Dict[str, Any]) -> str:
        # Compact facts to pass as context
        acct = facts.get("account", {})
        pos_lines = [
            f"- {p['symbol']}: {p['qty']} @ ${p['entry']:.2f} | ${p['upl']:+.2f} ({p['upl_pct']:+.2f}%)"
            for p in facts.get("positions", [])
        ]
        trade_lines = [
            f"- {t.get('symbol')} {t.get('action')} {t.get('qty')} @ ${t.get('price')} on {t.get('timestamp')}"
            for t in facts.get("recent_trades", [])
        ]
        lines = [
            f"Current time: {facts.get('now')}",
            f"Account: Equity ${acct.get('equity')}, BP {acct.get('buying_power')}, Cash {acct.get('cash')}",
            f"Open positions ({len(pos_lines)}):\n" + ("\n".join(pos_lines) if pos_lines else "None"),
            f"Recent trades: \n" + ("\n".join(trade_lines) if trade_lines else "None"),
            f"Detected intent: {facts.get('intent')}",
            "Answer the user's question based on these facts. If they asked about a symbol, prioritize it.",
            "If the question is off-topic, politely decline and redirect to trading topics.",
        ]
        return f"User question: {content}\n\nContext:\n" + "\n".join(lines)


# Singleton
_conversation_service: Optional[DiscordConversationService] = None

def get_discord_conversation_service(bot=None) -> Optional[DiscordConversationService]:
    global _conversation_service
    if _conversation_service is None and bot is not None:
        _conversation_service = DiscordConversationService(bot)
    return _conversation_service
