import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { 
  Monitor, 
  Copy, 
  Zap, 
  Globe, 
  Shield, 
  MonitorSpeaker,
  ArrowRight,
  CheckCircle,
  Download
} from 'lucide-react';

const LandingPage = () => {

  const { authUser } = useAuth();

  const features = [
    {
      icon: Monitor,
      title: "Extract Text From Anywhere on Your Screen",
      description: "Simply select an area on your screen and TextExtract instantly copies all visible text to your clipboard.",
    },
    {
      icon: Copy,
      title: "Copy to Clipboard Instantly",
      description: "No need to click \"copy\"—TextExtract puts extracted text right into your clipboard, ready to paste.",
    },
    {
      icon: Globe,
      title: "Supports Multiple Languages",
      description: "TextExtract is built with multilingual OCR capabilities—perfect for users around the world.",
    },
    {
      icon: Zap,
      title: "Accurate and Fast OCR with AI",
      description: "Powered by advanced AI technology for quick and reliable text extraction from images, PDFs, or apps.",
    },
    {
      icon: MonitorSpeaker,
      title: "Multi-Monitor Support",
      description: "Using more than one screen? Easily choose which monitor to capture from within the app.",
    },
    {
      icon: Shield,
      title: "Secure & Private",
      description: "Your data is processed securely and never get stored in the system. Your privacy is our top priority.",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-12 lg:py-16">
        <div className="text-center max-w-4xl mx-auto">
          <Badge variant="secondary" className="mb-4 px-4 py-2 text-sm font-medium">
            🚀 Now Available
          </Badge>
          
          <h1 className="text-5xl lg:text-7xl font-bold bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 bg-clip-text text-transparent mb-6 leading-tight">
            Welcome to TextExtract
          </h1>
          
          <p className="text-xl lg:text-2xl text-slate-600 mb-8 max-w-2xl mx-auto leading-relaxed">
            Extract text from any video or screen with ease.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">

             <a 
              href="https://github.com/Zidny000/textextract-releases/releases/download/v1.0.0/TextExtract_Setup.exe" 
              download="TextExtract.exe"
              className="group"
            >
              <Button
                size="lg" 
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-8 py-3 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-0.5"
              >
                Download
                <Download className="ml-2 h-5 w-5" />
              </Button>           
            </a>

            {!authUser && (
              <RouterLink to="/login">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-2 border-slate-300 hover:border-slate-400 px-8 py-3 text-lg font-semibold transition-all duration-300 hover:bg-slate-50"
                >
                  Login
                </Button>
              </RouterLink>
            )}
          </div>

          
          <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span>Free to try • No credit card required</span>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="container mx-auto px-4 py-12 lg:py-16">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold text-slate-900 mb-4">
            Spend More Time on Understanding, Not on Typing
          </h2>
          <h2 className="text-3xl lg:text-4xl font-bold text-slate-900 mb-4">
            Saves Upto 80% of Your Time
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Powerful features designed to make text extraction seamless and efficient for professionals and everyday users alike.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
          {features.map((feature, index) => {
            const IconComponent = feature.icon;
            return (
              <Card 
                key={index} 
                className="group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border-0 shadow-lg bg-white/80 backdrop-blur-sm hover:bg-white"
              >
                <CardHeader className="pb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                    <IconComponent className="h-6 w-6 text-white" />
                  </div>
                  <CardTitle className="text-xl font-semibold text-slate-900 group-hover:text-blue-700 transition-colors duration-300">
                    {feature.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-slate-600 text-base leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 py-16 lg:py-24">
        <div className="container mx-auto px-4 text-center">
          <h3 className="text-3xl lg:text-4xl font-bold text-white mb-4">
            Ready to extract text like a pro?
          </h3>
          <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
            Join thousands of users who trust TextExtract for their daily text extraction needs.
          </p>
          <a 
              href="https://github.com/Zidny000/textextract-releases/releases/download/v1.0.0/TextExtract_Setup.exe" 
              download="TextExtract.exe"
              className="group"
            >
            <Button 
              size="lg"
              className="bg-white text-slate-900 hover:bg-slate-100 px-8 py-3 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-0.5"
            >
              Start Extracting Now
              <Download className="ml-2 h-5 w-5" />
            </Button>
          </a>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;