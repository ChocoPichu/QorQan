document.addEventListener('alpine:init', () => {
    Alpine.data('operatorDashboard', () => ({
        isLoggedIn: false,
        operatorName: '',
        loginData: { username: '', password: '' },
        loginError: '',

        // Sidebar tabs
        activeTab: 'tickets',

        // Ticket state
        tickets: [],
        activeTicket: null,
        messages: [],
        newMessage: '',
        pollingInterval: null,

        // Phase 3: Blacklist state
        blacklist: [],
        banModal: { open: false, reason: '' },

        async init() {
            await this.checkAuth();

            this.pollingInterval = setInterval(() => {
                if (this.isLoggedIn) {
                    this.fetchTickets();
                    if (this.activeTicket && this.activeTicket.status === 'active') {
                        this.fetchMessages();
                    }
                }
            }, 3000);
        },

        async checkAuth() {
            try {
                const res = await fetch('/api/auth/me');
                const data = await res.json();
                if (data.status === 'success') {
                    this.isLoggedIn = true;
                    this.operatorName = data.operator_name;
                    this.fetchTickets();
                }
            } catch (err) {
                console.log("Not logged in");
            }
        },

        async login() {
            this.loginError = '';
            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.loginData)
                });
                const data = await res.json();

                if (data.status === 'success') {
                    this.isLoggedIn = true;
                    this.operatorName = data.operator_name;
                    this.loginData = { username: '', password: '' };
                    this.fetchTickets();
                } else {
                    this.loginError = data.message;
                }
            } catch (err) {
                this.loginError = 'Server connection failed.';
            }
        },

        async logout() {
            await fetch('/api/auth/logout', { method: 'POST' });
            this.isLoggedIn = false;
            this.operatorName = '';
            this.tickets = [];
            this.activeTicket = null;
            this.messages = [];
            this.blacklist = [];
        },

        // ── TICKETS ──────────────────────────────────────────────────────

        async fetchTickets() {
            try {
                const res = await fetch('/api/tickets');
                if (res.status === 401) {
                    this.isLoggedIn = false;
                    return;
                }
                const data = await res.json();
                if (data.status === 'success') {
                    const previousTickets = this.tickets;
                    this.tickets = data.tickets;

                    // Phase 2: Detect kid-closed active ticket
                    if (this.activeTicket) {
                        const updated = this.tickets.find(t => t.id === this.activeTicket.id);
                        if (updated) {
                            this.activeTicket = updated;
                        } else {
                            const kidName = this.activeTicket.full_name || 'The child';
                            this.showToast(`\u26a0\ufe0f ${kidName} has closed the chat.`, 'warn');
                            this.activeTicket = null;
                            this.messages = [];
                        }
                    }

                    // Phase 2: Detect newly-unread tickets, fire info toast
                    this.tickets.forEach(ticket => {
                        if (!ticket.has_unread) return;
                        if (this.activeTicket && this.activeTicket.id === ticket.id) return;
                        const prev = previousTickets.find(t => t.id === ticket.id);
                        if (prev && !prev.has_unread) {
                            this.showToast(`\ud83d\udcac New message from ${ticket.full_name}`, 'info');
                        }
                    });
                }
            } catch (err) {
                console.error("Error fetching tickets:", err);
            }
        },

        async selectTicket(ticket) {
            this.activeTicket = ticket;
            this.activeTab = 'tickets';
            await this.fetchMessages();
            this.scrollToBottom();

            // Phase 2: Mark messages read → clears red dot
            try {
                await fetch('/api/messages/mark_read', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: ticket.id })
                });
                const idx = this.tickets.findIndex(t => t.id === ticket.id);
                if (idx !== -1) this.tickets[idx].has_unread = 0;
            } catch (err) {
                console.error("Error marking messages read:", err);
            }
        },

        async acceptTicket(ticketId) {
            try {
                const res = await fetch('/api/ticket/accept', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: ticketId })
                });

                if (res.ok) {
                    await this.fetchTickets();
                    const accepted = this.tickets.find(t => t.id === ticketId);
                    if (accepted) this.selectTicket(accepted);
                }
            } catch (err) {
                console.error("Error accepting ticket:", err);
            }
        },

        async fetchMessages() {
            if (!this.activeTicket) return;
            try {
                const res = await fetch(`/api/messages/${this.activeTicket.id}`);
                const data = await res.json();

                if (data.status === 'success') {
                    const oldLength = this.messages.length;
                    this.messages = data.messages;
                    if (this.messages.length > oldLength) {
                        setTimeout(() => this.scrollToBottom(), 50);
                    }
                }
            } catch (err) {
                console.error("Error fetching messages:", err);
            }
        },

        async sendMessage() {
            if (!this.newMessage.trim() || !this.activeTicket) return;

            const textToSend = this.newMessage.trim();
            this.newMessage = '';

            try {
                await fetch('/api/messages/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.activeTicket.id,
                        text: textToSend
                    })
                });
                await this.fetchMessages();
            } catch (err) {
                this.newMessage = textToSend;
            }
        },

        async closeTicket(ticketId) {
            if (!confirm("Are you sure you want to close this session?")) return;

            try {
                await fetch('/api/ticket/close', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: ticketId })
                });

                this.activeTicket = null;
                this.messages = [];
                await this.fetchTickets();
            } catch (err) {
                console.error("Error closing ticket:", err);
            }
        },

        scrollToBottom() {
            const container = document.getElementById('chat-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        },

        // ── PHASE 3: BLACKLIST / BAN HAMMER ──────────────────────────────

        openBanModal() {
            this.banModal.reason = '';
            this.banModal.open = true;
        },

        async confirmBan() {
            if (!this.activeTicket) return;

            try {
                const res = await fetch('/api/user/ban', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.activeTicket.id,
                        reason: this.banModal.reason || 'No reason provided'
                    })
                });
                const data = await res.json();

                this.banModal.open = false;

                if (data.status === 'success') {
                    this.showToast(`\ud83d\udd28 ${data.message}`, 'success');
                    // Kick them from the active view
                    this.activeTicket = null;
                    this.messages = [];
                    await this.fetchTickets();
                } else {
                    this.showToast(`Error: ${data.message}`, 'error');
                }
            } catch (err) {
                this.banModal.open = false;
                this.showToast('Failed to ban user.', 'error');
                console.error("Error banning user:", err);
            }
        },

        async fetchBlacklist() {
            try {
                const res = await fetch('/api/blacklist');
                const data = await res.json();
                if (data.status === 'success') {
                    this.blacklist = data.blacklist;
                }
            } catch (err) {
                console.error("Error fetching blacklist:", err);
            }
        },

        async unbanUser(telegramId) {
            if (!confirm("Remove this user from the blacklist?")) return;

            try {
                const res = await fetch('/api/user/unban', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ telegram_id: telegramId })
                });
                const data = await res.json();

                if (data.status === 'success') {
                    this.showToast('✅ User unbanned.', 'success');
                    await this.fetchBlacklist();
                } else {
                    this.showToast(`Error: ${data.message}`, 'error');
                }
            } catch (err) {
                this.showToast('Failed to unban user.', 'error');
                console.error("Error unbanning user:", err);
            }
        },

        // ── TOAST SYSTEM ─────────────────────────────────────────────────

        showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            if (!container) return;

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            container.appendChild(toast);

            setTimeout(() => {
                toast.style.transition = 'opacity 0.4s ease';
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 400);
            }, 5000);
        }
    }));
});