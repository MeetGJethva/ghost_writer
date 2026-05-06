const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");

class WebJSProvider {
  constructor() {
    this.client = new Client({
      authStrategy: new LocalAuth(),
      puppeteer: { headless: true, args: ["--no-sandbox"] },
    });

    this.client.on("qr", (qr) => qrcode.generate(qr, { small: true }));
    this.client.on("ready", () => console.log("WhatsApp Web is ready!"));
    this.client.initialize();
  }

  // Convert standard Markdown to WhatsApp formatting
  formatMessage(text) {
    if (!text) return "";

    return text
      // 1. Headers: ### Header -> *HEADER*
      .replace(/^#{1,6}\s+(.*)$/gm, (match, p1) => `*${p1.toUpperCase()}*`)
      // 2. Bold: **text** -> *text*
      .replace(/\*\*(.*?)\*\*/g, "*$1*")
      // 3. Bullet points: - item -> • item
      .replace(/^\s*[-*]\s+/gm, "• ")
      // 4. Clean up multiple empty lines
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  // Standardized method to send messages
  async sendMessage(number, message) {
    try {
      const formattedMessage = this.formatMessage(message);
      let chatId = number;
      if (!chatId.includes("@")) {
        const numberId = await this.client.getNumberId(chatId);
        if (numberId) {
          chatId = numberId._serialized;
        } else {
          chatId = `${chatId}@c.us`;
        }
      }
      console.log(`Sending to: ${chatId}`);
      const response = await this.client.sendMessage(chatId, formattedMessage);
      return { success: true, response };
    } catch (error) {
      console.error("Error in sendMessage:", error);
      return { success: false, error: error.message };
    }
  }

  // Listener for incoming messages
  onMessage(callback) {
    this.client.on("message", callback);
  }
}

module.exports = WebJSProvider;