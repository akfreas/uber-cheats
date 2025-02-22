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
  const [urlHash, setUrlHash] = useState<string>('');

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
      setError('Connection error occurred');
      setIsLoading(false);
    };

    websocket.onclose = () => {
      setWs(null);
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

    // Wait for WebSocket connection to be established
    await new Promise<void>((resolve) => {
      websocket.onopen = () => resolve();
      websocket.onerror = () => {
        setError('Failed to establish connection with server');
        setIsLoading(false);
        resolve();
      };
    });

    if (websocket.readyState !== WebSocket.OPEN) {
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
        // Generate hash from URL
        const hash = await generateHash(url);
        setUrlHash(hash);
        navigate(`/deals#${hash}`);
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

  // Function to generate hash from URL
  const generateHash = async (url: string): Promise<string> => {
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
    if (data.status === 'success' && data.hash) {
      return data.hash;
    }
    throw new Error('No hash returned from server');
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

          {urlHash && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" align="center">
                Share this link to view these deals:
              </Typography>
              <Link href={`/deals#${urlHash}`}>
                {window.location.origin}/deals#{urlHash}
              </Link>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default UrlInput; 