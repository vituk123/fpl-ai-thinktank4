// Simple test endpoint to verify Vercel serverless functions work
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  return res.json({ 
    message: 'API endpoint is working!',
    timestamp: new Date().toISOString()
  });
}

