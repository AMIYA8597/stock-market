require('dotenv').config();
const express = require('express');
const cors = require('cors');
const session = require('express-session');
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use(session({
  secret: process.env.SESSION_SECRET || 'secret',
  resave: false,
  saveUninitialized: true,
}));
app.use(passport.initialize());
app.use(passport.session());

// Passport configuration
passport.use(new GoogleStrategy({
  clientID: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  callbackURL: '/auth/google/callback',
}, (accessToken, refreshToken, profile, cb) => {
  // In a real app you would lookup or create a user record here.
  return cb(null, profile);
}));
passport.serializeUser((user, cb) => cb(null, user));
passport.deserializeUser((obj, cb) => cb(null, obj));

// Auth routes
app.get('/auth/google', passport.authenticate('google', { scope: ['profile', 'email'] }));
app.get('/auth/google/callback',
  passport.authenticate('google', { failureRedirect: '/' }),
  (req, res) => {
    // Successful authentication, redirect to client with minimal info.
    const user = { id: req.user.id, displayName: req.user.displayName, emails: req.user.emails };
    // In production you might issue a JWT; here we just send JSON.
    res.redirect(`${process.env.CLIENT_URL || 'http://localhost:5173'}/?user=${encodeURIComponent(JSON.stringify(user))}`);
  }
);

// Protected route example
app.get('/api/user', (req, res) => {
  if (!req.isAuthenticated()) {
    return res.status(401).json({ error: 'Not authenticated' });
  }
  res.json({ user: req.user });
});

// Alpha Vantage proxy endpoint
app.get('/api/stock/:symbol', async (req, res) => {
  const symbol = req.params.symbol;
  const apiKey = process.env.ALPHA_VANTAGE_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'Alpha Vantage API key not configured.' });
  }
  try {
    const response = await axios.get('https://www.alphavantage.co/query', {
      params: {
        function: 'TIME_SERIES_INTRADAY',
        symbol,
        interval: '5min',
        outputsize: 'compact',
        apikey: apiKey,
      },
    });
    res.json(response.data);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch data from Alpha Vantage.' });
  }
});

app.listen(PORT, () => {
  console.log(`Express server listening on port ${PORT}`);
});
