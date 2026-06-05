const { Client, GatewayIntentBits } = require('discord.js');
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });

// ✅ Put your banned words here
const bannedWords = [
  "word1", // replace with your actual words
  "word2",
  "word3"
];

// ✅ Regex to catch banned words inside other words, case-insensitive
const bannedRegex = new RegExp(bannedWords.join("|"), "i");

client.on("messageCreate", async (message) => {
  if (message.author.bot) return;

  // Check if message contains banned words OR non-English characters
  if (bannedRegex.test(message.content) || /[^\u0000-\u007F]/.test(message.content)) {
    try {
      await message.delete();
      await message.channel.send("*A strong gust of wind suddenly sweeps dust into your eyes; you reflexively blink it away while wondering what had happened.");
    } catch (err) {
      console.error("Failed to delete message:", err);
    }
  }
});

client.login("YOUR_BOT_TOKEN");
