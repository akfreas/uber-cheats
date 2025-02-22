import { ThemeProvider, createTheme } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import DealsTable from './components/DealsTable';
import UrlInput from './components/UrlInput';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00ff87',
    },
    secondary: {
      main: '#ff00ff',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<UrlInput />} />
          <Route path="/deals" element={<DealsTable />} />
          <Route path="/deals/:hash" element={<DealsTable />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
