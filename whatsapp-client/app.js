require("dotenv").config();
const express = require("express");
const axios = require("axios");

const MessagingProvider = require("./providers/WebJSProvider");

const app = express();
app.use(express.json());
app.get("/test", (req, res) => res.send("Server is alive!"));

const messenger = new MessagingProvider();

messenger.onMessage(async (msg) => {
  try {
    const rawNumber = msg.from.split("@")[0];
    console.log("rawNumber: ", msg.from);
    const mobileNumber =
      rawNumber.length > 10 ? rawNumber.slice(-10) : rawNumber;

    const allowedNumber = process.env.ALLOWED_PHONE_NUMBER;

    if (!allowedNumber) {
      console.log("No ALLOWED_PHONE_NUMBER specified in .env, ignoring message.");
      return;
    }

    if (rawNumber !== allowedNumber && mobileNumber !== allowedNumber) {
      console.log(`Ignoring message from ${rawNumber}, does not match ALLOWED_PHONE_NUMBER.`);
      return;
    }

    const backendUrl = process.env.BACKEND_URL;
    if (!backendUrl) {
      console.log("No BACKEND_URL specified in .env, cannot forward message.");
      return;
    }

    const now = new Date();
    
    const payload = {
      query: msg.body,
      source_id: rawNumber,
      source: "WHATSAPP",
      metadata: {
        date: now.toISOString().split("T")[0],
        time: now.toTimeString().split(" ")[0]
      }
    };
    console.log("payload: ", payload);
    await axios.post(`${backendUrl}/api/tasks`, payload);

  } catch (error) {
    console.error("Error processing message:", error.response?.data || error.message);
  }
});

// API for sending messages back to user
app.post("/api/send-message", async (req, res) => {
  try {
    const { to, message } = req.body;
    
    if (!to || !message) {
      return res.status(400).json({ error: "Missing 'to' or 'message' in request body" });
    }

    // If 'to' is just a raw number like "917229091491", append "@c.us"
    const chatId = to.includes('@') ? to : `${to}@c.us`;

    await messenger.sendMessage(chatId, message);
    
    res.json({ success: true, message: "Message sent successfully" });
  } catch (error) {
    console.error("Error sending message:", error.message);
    res.status(500).json({ error: "Failed to send message", details: error.message });
  }
});

const PORT = process.env.PORT || 8080;
app.listen(9007, () => console.log(`Service running on port ${PORT}`));