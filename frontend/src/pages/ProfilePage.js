import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Alert, AlertDescription } from "../components/ui/alert";
import { toast } from 'sonner';
import { 
  User, 
  Mail, 
  Shield, 
  BarChart3, 
  CreditCard, 
  Star,
  LogOut,
  Key,
  CheckCircle,
  XCircle,
  Calendar,
  Activity
} from 'lucide-react';

// Review form component
const ReviewForm = ({ axiosAuth }) => {
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [userReview, setUserReview] = useState(null);

  useEffect(() => {
    // Check if user has already submitted a review
    const fetchReview = async () => {
      try {
        const response = await axiosAuth.get('/users/reviews');
        if (response.data && response.data.length > 0) {
          const existingReview = response.data[0];
          setUserReview(existingReview);
          setRating(existingReview.rating);
          setReviewText(existingReview.review_text);
        }
      } catch (error) {
        console.error('Error fetching user reviews:', error);
      }
    };
    
    fetchReview();
  }, [axiosAuth]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    
    try {
      await axiosAuth.post('/users/reviews', {
        rating,
        review_text: reviewText
      });
      
      toast.success("Review submitted successfully!");

      // Update local state to show the review was submitted
      setUserReview({
        rating,
        review_text: reviewText,
        created_at: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error submitting review:', error);
      toast.error("Failed to submit review. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-slate-900">
          <Star className="h-5 w-5 text-yellow-500" />
          Share Your Experience
        </CardTitle>
        <CardDescription>
          Help us improve by sharing your feedback about TextExtract
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <Label className="text-slate-700 font-medium">Your Rating</Label>
            <div className="flex items-center gap-1 mt-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  className={`p-1 transition-colors ${
                    star <= rating ? 'text-yellow-400' : 'text-gray-300'
                  } hover:text-yellow-400`}
                >
                  <Star className="h-6 w-6 fill-current" />
                </button>
              ))}
              <span className="ml-2 text-sm text-slate-600">({rating}/5)</span>
            </div>
          </div>
          
          <div>
            <Label htmlFor="review-text" className="text-slate-700 font-medium">
              Your Review
            </Label>
            <textarea
              id="review-text"
              className="w-full mt-2 p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-all duration-200"
              rows={4}
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder="Tell us about your experience with TextExtract..."
              required
            />
          </div>
          
          <Button 
            type="submit"
            disabled={submitting || reviewText.length < 5}
            className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold px-6 py-2 transition-all duration-300"
          >
            {submitting ? 'Submitting...' : (userReview ? 'Update Review' : 'Submit Review')}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

const ProfilePage = () => {
  const { user, logout, axiosAuth } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [usageStats, setUsageStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUsageStats = async () => {
      try {
        setError('');
        const response = await axiosAuth.get('/users/profile');
        if (response.data && response.data.usage) {
          setUsageStats(response.data.usage);
        } else {
          setError('No usage data available');
        }
      } catch (error) {
        console.error('Error fetching usage stats:', error);
        setError('Failed to load usage statistics. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchUsageStats();
    }
  }, [user, axiosAuth]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!user) {
    return null;
  }

  const getUsagePercentage = () => {
    if (!usageStats) return 0;
    return Math.min((usageStats.monthly_requests / usageStats.plan_limit) * 100, 100);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl lg:text-5xl font-bold bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 bg-clip-text text-transparent mb-4">
            My Profile
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Manage your TextExtract account, view usage statistics, and customize your experience
          </p>
        </div>

        {message && (
          <Alert className="mb-6 border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">{message}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Account Information Card */}
          <Card className="group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1 border-0 shadow-lg bg-white/80 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <User className="h-6 w-6 text-white" />
              </div>
              <CardTitle className="text-xl font-semibold text-slate-900">Account Information</CardTitle>
              <CardDescription>Your personal account details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <User className="h-4 w-4 text-slate-500" />
                <div>
                  <p className="text-sm text-slate-500">Name</p>
                  <p className="font-medium text-slate-900">{user.full_name}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <Mail className="h-4 w-4 text-slate-500" />
                <div>
                  <p className="text-sm text-slate-500">Email</p>
                  <p className="font-medium text-slate-900">{user.email}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <CreditCard className="h-4 w-4 text-slate-500" />
                <div>
                  <p className="text-sm text-slate-500">Plan</p>
                  <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-200">
                    {user.plan_type?.toUpperCase() || 'FREE'}
                  </Badge>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <Activity className="h-4 w-4 text-slate-500" />
                <div>
                  <p className="text-sm text-slate-500">Status</p>
                  <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-200">
                    {user.status || 'ACTIVE'}
                  </Badge>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <Shield className="h-4 w-4 text-slate-500" />
                <div className="flex items-center gap-2">
                  <div>
                    <p className="text-sm text-slate-500">Email Verified</p>
                    <p className="font-medium text-slate-900 flex items-center gap-1">
                      {user.email_verified ? (
                        <>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          Verified
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 text-red-500" />
                          Not Verified
                        </>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Usage Statistics Card */}
          <Card className="group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1 border-0 shadow-lg bg-white/80 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <BarChart3 className="h-6 w-6 text-white" />
              </div>
              <CardTitle className="text-xl font-semibold text-slate-900">Usage Statistics</CardTitle>
              <CardDescription>Track your monthly API usage</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  <div className="h-4 bg-slate-200 rounded animate-pulse"></div>
                  <div className="h-4 bg-slate-200 rounded animate-pulse w-3/4"></div>
                </div>
              ) : usageStats ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-slate-700">Monthly API Requests</span>
                      <span className="text-sm text-slate-500">
                        {usageStats.monthly_requests} / {usageStats.plan_limit}
                      </span>
                    </div>
                    <Progress 
                      value={getUsagePercentage()} 
                      className="h-3"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg">
                      <p className="text-sm text-blue-600 font-medium">Used</p>
                      <p className="text-2xl font-bold text-blue-800">{usageStats.monthly_requests}</p>
                    </div>
                    <div className="p-4 bg-gradient-to-r from-green-50 to-green-100 rounded-lg">
                      <p className="text-sm text-green-600 font-medium">Remaining</p>
                      <p className="text-2xl font-bold text-green-800">{usageStats.remaining_requests}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <Alert variant="destructive">
                  <XCircle className="h-4 w-4" />
                  <AlertDescription>{error || 'Failed to load usage statistics'}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Subscription Section */}
        <Card className="mt-8 group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1 border-0 shadow-lg bg-white/80 backdrop-blur-sm">
          <CardHeader className="pb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <CreditCard className="h-6 w-6 text-white" />
            </div>
            <CardTitle className="text-xl font-semibold text-slate-900">Subscription Details</CardTitle>
            <CardDescription>Manage your plan and billing information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-gradient-to-r from-slate-50 to-slate-100 rounded-xl p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-2xl font-bold text-slate-900">
                    {user.plan_type?.toUpperCase() || 'FREE'} PLAN
                  </h3>
                  <p className="text-slate-600">Current subscription</p>
                </div>
                <Badge variant="secondary" className="bg-blue-100 text-blue-800 text-sm px-3 py-1">
                  Active
                </Badge>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <BarChart3 className="h-4 w-4 text-slate-500" />
                  <div>
                    <p className="text-sm text-slate-500">Monthly OCR Requests</p>
                    <p className="font-semibold text-slate-900">{usageStats?.plan_limit || "Loading..."}</p>
                  </div>
                </div>
                
                {usageStats?.renewal_date && (
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-slate-500" />
                    <div>
                      <p className="text-sm text-slate-500">Renewal Date</p>
                      <p className="font-semibold text-slate-900">
                        {new Date(usageStats.renewal_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>
              
              <Button 
                onClick={() => navigate('/subscription')}
                className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold px-6 py-2 transition-all duration-300"
              >
                {user.plan_type === 'free' ? 'Upgrade Plan' : 'Manage Subscription'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <Card className="mt-8 border-0 shadow-lg bg-white/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-xl font-semibold text-slate-900">Account Actions</CardTitle>
            <CardDescription>Manage your account settings and security</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <Button
                onClick={() => navigate('/change-password')}
                variant="outline"
                className="border-2 border-blue-200 hover:border-blue-300 hover:bg-blue-50 transition-all duration-300 flex items-center gap-2"
              >
                <Key className="h-4 w-4" />
                Change Password
              </Button>
              <Button
                onClick={handleLogout}
                variant="outline"
                className="border-2 border-red-200 hover:border-red-300 hover:bg-red-50 text-red-600 hover:text-red-700 transition-all duration-300 flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Review Section */}
        <div className="mt-8">
          <ReviewForm axiosAuth={axiosAuth} />
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;