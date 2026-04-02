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

  // Standardized method to send messages
  async sendMessage(number, message) {
    try {
      console.log(number);
      const formattedNumber = number.includes("@c.us")
        ? number
        : `${number}@c.us`;
      const response = await this.client.sendMessage(formattedNumber, message);
      return { success: true, response };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Listener for incoming messages
  onMessage(callback) {
    this.client.on("message", callback);
  }
}

module.exports = WebJSProvider;