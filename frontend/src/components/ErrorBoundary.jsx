import React from 'react';
import { Box, Typography, Button, Container } from '@mui/material';
import TerminalLayout from './TerminalLayout';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <TerminalLayout>
          <Container maxWidth="md" sx={{ py: 8 }}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h1" component="h1" gutterBottom sx={{ color: 'error.main' }}>
                Something went wrong
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
                An error occurred while rendering the application.
              </Typography>
              {this.state.error && (
                <Box
                  sx={{
                    mt: 4,
                    p: 3,
                    bgcolor: 'background.paper',
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'divider',
                    textAlign: 'left',
                    mb: 4,
                  }}
                >
                  <Typography variant="h6" gutterBottom>
                    Error Details:
                  </Typography>
                  <Typography
                    variant="body2"
                    component="pre"
                    sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {this.state.error.toString()}
                    {this.state.errorInfo?.componentStack && (
                      <>
                        {'\n\nComponent Stack:'}
                        {this.state.errorInfo.componentStack}
                      </>
                    )}
                  </Typography>
                </Box>
              )}
              <Button variant="outlined" onClick={this.handleReset}>
                Return to Home
              </Button>
            </Box>
          </Container>
        </TerminalLayout>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

