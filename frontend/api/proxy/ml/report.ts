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

    // Forward the request to ByteHosty
    const response = await fetch(url.toString(), {
      method: req.method,
      headers: {
        'Content-Type': req.headers['content-type'] || 'application/json',
        ...(req.headers.authorization && { Authorization: req.headers.authorization }),
      },
      body: req.method !== 'GET' && req.method !== 'HEAD' 
        ? JSON.stringify(req.body) 
        : undefined,
    });

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

