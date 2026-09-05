/**
 * api.js — Base configuration for backend communication.
 * Legacy prediction wrappers have been removed. 
 * Fetch calls are made directly in domain-specific scripts (e.g. recommend.js)
 */

const API_BASE = `${window.location.protocol}//${window.location.hostname || '127.0.0.1'}:5000`;
