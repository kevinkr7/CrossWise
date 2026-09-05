/**
 * api.js — Base configuration for backend communication.
 * 
 * Automatically detects local development vs production environments.
 * Priority order for backend URL:
 *   1. window.CROSSWISE_API_URL (injected via window or global script)
 *   2. localStorage.getItem('crosswise_api_url') (runtime console override)
 *   3. If on localhost/127.0.0.1 -> http://127.0.0.1:5000
 *   4. In production -> PROD_BACKEND_URL (set this to your Oracle VM domain/IP)
 */

// Replace this with your production backend domain / Oracle VM public domain
// e.g., 'https://api.yourdomain.com' or 'http://YOUR_ORACLE_IP:5000'
const PROD_BACKEND_URL = 'https://api.yourdomain.com';

const IS_LOCAL = [
  'localhost',
  '127.0.0.1',
  '0.0.0.0',
  ''
].includes(window.location.hostname);

const API_BASE = window.CROSSWISE_API_URL
  || localStorage.getItem('crosswise_api_url')
  || (IS_LOCAL ? `${window.location.protocol}//${window.location.hostname || '127.0.0.1'}:5000` : PROD_BACKEND_URL);

// Expose globally for cross-script consistency
window.API_BASE = API_BASE;
