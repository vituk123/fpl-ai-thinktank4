/**
 * Input validation utilities
 */

export const validateEntryId = (value) => {
  if (!value) {
    return { valid: false, error: 'Entry ID is required' };
  }

  const numValue = typeof value === 'string' ? parseInt(value, 10) : value;
  
  if (isNaN(numValue)) {
    return { valid: false, error: 'Entry ID must be a number' };
  }

  if (numValue <= 0) {
    return { valid: false, error: 'Entry ID must be greater than 0' };
  }

  if (numValue > 999999999) {
    return { valid: false, error: 'Entry ID is too large' };
  }

  return { valid: true, error: null };
};

export const validateGameweek = (value, min = 1, max = 38) => {
  if (!value) {
    return { valid: false, error: 'Gameweek is required' };
  }

  const numValue = typeof value === 'string' ? parseInt(value, 10) : value;
  
  if (isNaN(numValue)) {
    return { valid: false, error: 'Gameweek must be a number' };
  }

  if (numValue < min || numValue > max) {
    return { valid: false, error: `Gameweek must be between ${min} and ${max}` };
  }

  return { valid: true, error: null };
};

export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email) {
    return { valid: false, error: 'Email is required' };
  }
  if (!emailRegex.test(email)) {
    return { valid: false, error: 'Invalid email format' };
  }
  return { valid: true, error: null };
};

export default {
  validateEntryId,
  validateGameweek,
  validateEmail,
};

