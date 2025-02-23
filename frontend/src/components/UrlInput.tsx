import {
  Box,
  Button,
  Container,
  LinearProgress,
  Link,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import config from '../config';

const UrlInput: React.FC = () => {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [sessionId] = useState(uuidv4());

  // Cleanup WebSocket on component unmount
  useEffect(() => {
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [ws]);

  const setupWebSocket = () => {
    const websocket = new WebSocket(config.endpoints.websocket(sessionId));
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data.progress * 100);
      setMessage(data.message);
    };

    websocket.onerror = () => {
      console.error('WebSocket error occurred');
      setError('Connection error occurred');
      // Don't set isLoading to false here, let the reconnection attempt handle it
    };

    websocket.onclose = () => {
      console.log('WebSocket closed, attempting to reconnect...');
      // Try to reconnect after 1 second
      setTimeout(() => {
        if (isLoading) {  // Only reconnect if we're still loading
          setWs(setupWebSocket());
        }
      }, 1000);
    };

    return websocket;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setProgress(0);
    setMessage('');
    
    // Setup WebSocket connection
    const websocket = setupWebSocket();
    setWs(websocket);

    // Wait for WebSocket connection to be established with timeout
    try {
      await Promise.race([
        new Promise<void>((resolve, reject) => {
          websocket.onopen = () => resolve();
          websocket.onerror = () => reject(new Error('Failed to establish connection'));
        }),
        new Promise<void>((_, reject) => 
          setTimeout(() => reject(new Error('Connection timeout')), 5000)
        )
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(config.endpoints.findDeals, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch deals');
      }

      const data = await response.json();
      if (data.status === 'success') {
        // Navigate using the hash from the response
        if (data.hash) {
          navigate(`/deals/${data.hash}`);
        } else {
          throw new Error('No hash returned from server');
        }
      } else {
        setError(data.message || 'An error occurred');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 4,
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            width: '100%',
            borderRadius: 2,
          }}
        >
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Uber Eats Deal Finder
          </Typography>
          
          <Typography variant="body1" gutterBottom align="center" sx={{ mb: 3 }}>
            Go to <Link href="https://www.ubereats.com" target="_blank" rel="noopener noreferrer">ubereats.com</Link> and enter your location, then copy and paste the link from the address bar into the field below.
          </Typography>
          
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Uber Eats URL"
              variant="outlined"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isLoading}
              sx={{ mb: 2 }}
            />
            
            <Button
              fullWidth
              type="submit"
              variant="contained"
              disabled={isLoading || !url}
              sx={{ mb: 2 }}
            >
              Find Deals
            </Button>
          </form>

          {isLoading && (
            <Box sx={{ width: '100%' }}>
              <LinearProgress 
                variant="determinate" 
                value={progress} 
                sx={{ mb: 2 }}
              />
              <Typography variant="body2" color="text.secondary" align="center">
                {message}
              </Typography>
            </Box>
          )}

          {error && (
            <Typography color="error" align="center">
              {error}
            </Typography>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default UrlInput; 