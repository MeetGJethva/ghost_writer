// This is your blueprint. Both official and unofficial logic must follow this.
class WhatsAppProvider {
  constructor() {
    if (this.constructor === WhatsAppProvider) {
      throw new Error("Cannot instantiate abstract class.");
    }
  }
  async sendMessage(to, text) {
    throw new Error("Method 'sendMessage()' must be implemented.");
  }
  onMessage(callback) {
    throw new Error("Method 'onMessage()' must be implemented.");
  }
}
module.exports = WhatsAppProvider;