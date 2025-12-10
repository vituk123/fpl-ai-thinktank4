import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1D1D1B',
      light: '#3a3a3a',
      dark: '#000000',
      contrastText: '#DADAD3',
    },
    secondary: {
      main: '#C1C1BF',
      light: '#DADAD3',
      dark: '#A0A09E',
      contrastText: '#1D1D1B',
    },
    background: {
      default: '#DADAD3',
      paper: '#DADAD3',
    },
    text: {
      primary: '#1D1D1B',
      secondary: 'rgba(29, 29, 27, 0.7)',
    },
    divider: '#1D1D1B',
    error: {
      main: '#E84C3D',
    },
  },
  typography: {
    fontFamily: [
      'Roboto',
      'system-ui',
      '-apple-system',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: 'clamp(2.0625rem, calc(2.0625rem + 1.78236vw - 7.37899px), 3.25rem)',
      fontWeight: 400,
      lineHeight: 0.9807692308,
    },
    h2: {
      fontSize: 'clamp(1.6875rem, calc(1.6875rem + 0.65666vw - 2.71857px), 2.125rem)',
      fontWeight: 500,
      lineHeight: 1.2352941176,
    },
    h3: {
      fontSize: 'clamp(1.5rem, calc(1.5rem + 0.5vw), 2rem)',
      fontWeight: 500,
    },
    h4: {
      fontSize: 'clamp(1.25rem, calc(1.25rem + 0.4vw), 1.75rem)',
      fontWeight: 500,
    },
    body1: {
      fontSize: 'clamp(1.0625rem, calc(1.0625rem + 0.28143vw - 1.1651px), 1.25rem)',
      fontWeight: 500,
      lineHeight: 1.3,
    },
    body2: {
      fontSize: 'clamp(0.875rem, calc(0.875rem + 0.28143vw - 1.1651px), 1.0625rem)',
      fontWeight: 500,
      lineHeight: 1.5294117647,
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
      fontSize: 'clamp(12px, calc(12px + 0.4vw), 14px)',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          padding: 'clamp(12px, calc(12px + 0.5vw), 16px) clamp(24px, calc(24px + 1vw), 32px)',
          border: '2px solid #1D1D1B',
          backgroundColor: '#C1C1BF',
          color: '#1D1D1B',
          fontWeight: 500,
          '&:hover': {
            backgroundColor: '#A0A09E',
            borderColor: '#1D1D1B',
          },
        },
        outlined: {
          borderColor: '#1D1D1B',
          color: '#1D1D1B',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'rgba(29, 29, 27, 0.1)',
            borderColor: '#1D1D1B',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#DADAD3',
          border: '2px solid #1D1D1B',
          borderRadius: 0,
          padding: 'clamp(16px, calc(16px + 1vw), 24px)',
          transition: 'all 0.2s ease',
          boxShadow: '-0.6rem 0.6rem 0 rgba(29, 30, 28, 0.26)',
          '&:hover': {
            boxShadow: '-0.8rem 0.8rem 0 rgba(29, 30, 28, 0.3)',
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 0,
            backgroundColor: '#DADAD3',
            '& fieldset': {
              borderColor: '#1D1D1B',
              borderWidth: '2px',
            },
            '&:hover fieldset': {
              borderColor: '#1D1D1B',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#1D1D1B',
            },
          },
          '& .MuiInputLabel-root': {
            color: 'rgba(29, 29, 27, 0.7)',
            '&.Mui-focused': {
              color: '#1D1D1B',
            },
          },
          '& .MuiInputBase-input': {
            color: '#1D1D1B',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#DADAD3',
          backgroundImage: 'none',
          border: '2px solid #1D1D1B',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#DADAD3',
          boxShadow: 'none',
          borderBottom: '2px solid #1D1D1B',
        },
      },
    },
  },
});

export default theme;

