import React from 'react';
import { Box, Typography, Link } from '@mui/material';

const Footer = () => {
  return (
    <Box
      component="footer"
      sx={{
        py: 2,
        mt: 'auto',
        textAlign: 'center',
        backgroundColor: 'primary.main',
        color: 'white',
      }}
    >
      <Typography variant="body2">
        © 2025 TextExtract · Contact: <Link 
          href="mailto:t.m.zidny@gmail.com" 
          color="inherit" 
          underline="hover"
        >
          t.m.zidny@gmail.com
        </Link>
      </Typography>
    </Box>
  );
};

export default Footer;
