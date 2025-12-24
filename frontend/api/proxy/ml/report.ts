// Vercel Serverless Function to proxy ML report requests to ByteHosty
import type { VercelRequest, VercelResponse } from '@vercel/node';

const BYTEHOSTY_URL = 'http://198.23.185.233:8080';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  // Handle CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    // Build the ByteHosty URL
    const url = new URL('/api/v1/ml/report', BYTEHOSTY_URL);
    
    // Forward query parameters
    Object.entries(req.query).forEach(([key, value]) => {
      if (value) {
        if (Array.isArray(value)) {
          value.forEach(v => url.searchParams.append(key, String(v)));
        } else {
          url.searchParams.append(key, String(value));
        }
      }
    });

    console.log(`[Proxy] ${req.method} ${url.toString()}`);

    // Forward the request to ByteHosty with extended timeout for ML reports
    // ML reports can take 30-60 seconds, so we need a longer timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout for ML reports
    
    let response: Response;
    try {
      console.log(`[Proxy] Fetching from: ${url.toString()}`);
      // Vercel serverless functions can connect to HTTP endpoints
      // The issue might be DNS resolution or network restrictions
      // Try using the IP directly and ensure proper error handling
      const fetchUrl = url.toString();
      console.log(`[Proxy] Attempting fetch to: ${fetchUrl}`);
      
      response = await fetch(fetchUrl, {
        method: req.method,
        headers: {
          'Content-Type': req.headers['content-type'] || 'application/json',
          ...(req.headers.authorization && { Authorization: req.headers.authorization }),
          'User-Agent': 'Vercel-Proxy/1.0',
        },
        body: req.method !== 'GET' && req.method !== 'HEAD' 
          ? JSON.stringify(req.body) 
          : undefined,
        signal: controller.signal,
        // Vercel fetch should support HTTP by default
        redirect: 'follow',
      });
      clearTimeout(timeoutId);
      console.log(`[Proxy] Response status: ${response.status}`);
    } catch (fetchError: any) {
      clearTimeout(timeoutId);
      console.error('[Proxy] Fetch error:', fetchError);
      console.error('[Proxy] Error name:', fetchError.name);
      console.error('[Proxy] Error message:', fetchError.message);
      
      // Check if it's a network/connection error
      if (fetchError.name === 'AbortError' || fetchError.name === 'TimeoutError') {
        return res.status(504).json({
          error: 'Proxy timeout',
          message: 'Request to ByteHosty server timed out after 120 seconds',
          url: url.toString()
        });
      }
      
      // Check for specific connection errors
      if (fetchError.message && (
        fetchError.message.includes('ECONNREFUSED') ||
        fetchError.message.includes('ENOTFOUND') ||
        fetchError.message.includes('ETIMEDOUT') ||
        fetchError.message.includes('fetch failed')
      )) {
        return res.status(502).json({
          error: 'Proxy connection error',
          message: 'Failed to connect to ByteHosty server. The server may be down or unreachable.',
          details: fetchError.message,
          url: url.toString()
        });
      }
      
      return res.status(502).json({
        error: 'Proxy error',
        message: fetchError.message || 'Failed to proxy request to ByteHosty server',
        details: fetchError.name || 'Unknown error',
        url: url.toString()
      });
    }

    // Get response data
    const contentType = response.headers.get('content-type') || '';
    let data: any;
    
    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      if (text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html')) {
        console.error('[Proxy] Received HTML instead of JSON:', text.substring(0, 200));
        return res.status(502).json({
          error: 'Proxy error',
          message: 'Backend returned HTML instead of JSON.',
          url: url.toString()
        });
      }
      data = text;
    }

    // Forward status and headers
    res.status(response.status);
    
    const headersToForward = ['content-type', 'cache-control'];
    headersToForward.forEach(header => {
      const value = response.headers.get(header);
      if (value) {
        res.setHeader(header, value);
      }
    });

    if (contentType.includes('application/json')) {
      return res.json(data);
    } else {
      return res.send(data);
    }
  } catch (error: any) {
    console.error('[Proxy] Error:', error);
    return res.status(500).json({
      error: 'Proxy error',
      message: error.message || 'Failed to proxy request to ByteHosty',
    });
  }
}

