import React, { useState, useEffect, useRef } from 'react';
import { User, Plus, Search, Target, Calendar, ChefHat, Calculator, Settings, LogOut, Eye, EyeOff, Camera, Home, BookOpen, TrendingUp, Award, Bell, Upload, X } from 'lucide-react';

const Bodari = () => {
  const [currentView, setCurrentView] = useState('auth');
  const [authMode, setAuthMode] = useState('signin');
  const [showPassword, setShowPassword] = useState(false);
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [fridgeItems, setFridgeItems] = useState([]);
  const [mealPlan, setMealPlan] = useState([]);
  const [activeTab, setActiveTab] = useState('home');
  const [showImageUpload, setShowImageUpload] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  
  // Auth form state
  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    confirmPassword: ''
  });

  // Profile setup state
  const [profileForm, setProfileForm] = useState({
    name: '',
    age: '',
    gender: '',
    height: '',
    weight: '',
    activityLevel: '',
    goal: '',
    dietaryRestrictions: [],
    allergies: '',
    mealsPerDay: '3',
    waterGoal: '8'
  });

  // Meal planning state
  const [newFridgeItem, setNewFridgeItem] = useState('');
  const [mealSearch, setMealSearch] = useState('');
  const [workoutLog, setWorkoutLog] = useState([]);
  const [waterIntake, setWaterIntake] = useState(0);
  const [dailyProgress, setDailyProgress] = useState({
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0
  });

  // Sample food database (expanded)
  const foodDatabase = [
    { name: 'Chicken Breast', calories: 165, protein: 31, carbs: 0, fat: 3.6, category: 'protein' },
    { name: 'Brown Rice', calories: 112, protein: 2.3, carbs: 23, fat: 0.9, category: 'carbs' },
    { name: 'Broccoli', calories: 34, protein: 2.8, carbs: 7, fat: 0.4, category: 'vegetable' },
    { name: 'Salmon', calories: 208, protein: 22, carbs: 0, fat: 12, category: 'protein' },
    { name: 'Sweet Potato', calories: 86, protein: 1.6, carbs: 20, fat: 0.1, category: 'carbs' },
    { name: 'Spinach', calories: 23, protein: 2.9, carbs: 3.6, fat: 0.4, category: 'vegetable' },
    { name: 'Eggs', calories: 155, protein: 13, carbs: 1.1, fat: 11, category: 'protein' },
    { name: 'Oats', calories: 389, protein: 16.9, carbs: 66, fat: 6.9, category: 'carbs' },
    { name: 'Avocado', calories: 160, protein: 2, carbs: 9, fat: 15, category: 'fat' },
    { name: 'Greek Yogurt', calories: 59, protein: 10, carbs: 3.6, fat: 0.4, category: 'protein' },
    { name: 'Banana', calories: 89, protein: 1.1, carbs: 23, fat: 0.3, category: 'fruit' },
    { name: 'Almonds', calories: 579, protein: 21, carbs: 22, fat: 50, category: 'nuts' },
    { name: 'Quinoa', calories: 120, protein: 4.4, carbs: 22, fat: 1.9, category: 'carbs' },
    { name: 'Tuna', calories: 144, protein: 30, carbs: 0, fat: 1, category: 'protein' },
    { name: 'Apple', calories: 52, protein: 0.3, carbs: 14, fat: 0.2, category: 'fruit' }
  ];

  // Sample workout exercises
  const workoutExercises = [
    { name: 'Push-ups', category: 'chest', caloriesPerMin: 8 },
    { name: 'Squats', category: 'legs', caloriesPerMin: 10 },
    { name: 'Plank', category: 'core', caloriesPerMin: 5 },
    { name: 'Burpees', category: 'full-body', caloriesPerMin: 12 },
    { name: 'Lunges', category: 'legs', caloriesPerMin: 9 },
    { name: 'Mountain Climbers', category: 'cardio', caloriesPerMin: 11 },
    { name: 'Jumping Jacks', category: 'cardio', caloriesPerMin: 10 }
  ];

  useEffect(() => {
    // Check for existing user session
    const savedUser = JSON.parse(localStorage.getItem('bodariUser') || 'null');
    const savedProfile = JSON.parse(localStorage.getItem('userProfile') || 'null');
    const savedFridge = JSON.parse(localStorage.getItem('fridgeItems') || '[]');
    const savedProgress = JSON.parse(localStorage.getItem('dailyProgress') || '{"calories":0,"protein":0,"carbs":0,"fat":0}');
    const savedWater = parseInt(localStorage.getItem('waterIntake') || '0');
    
    if (savedUser) {
      setUser(savedUser);
      setUserProfile(savedProfile);
      setFridgeItems(savedFridge);
      setDailyProgress(savedProgress);
      setWaterIntake(savedWater);
      setCurrentView(savedProfile ? 'dashboard' : 'profile-setup');
    }
  }, []);

  const handleAuth = (e) => {
    if (e) e.preventDefault();
    if (authMode === 'signup' && authForm.password !== authForm.confirmPassword) {
      alert('Passwords do not match!');
      return;
    }
    
    const newUser = {
      id: Date.now(),
      email: authForm.email,
      createdAt: new Date().toISOString()
    };
    
    setUser(newUser);
    localStorage.setItem('bodariUser', JSON.stringify(newUser));
    setCurrentView('profile-setup');
  };

  const handleProfileSetup = (e) => {
    if (e) e.preventDefault();
    const calculatedBMR = calculateBMR(profileForm);
    const dailyCalories = calculateDailyCalories(calculatedBMR, profileForm.activityLevel, profileForm.goal);
    
    const profile = {
      ...profileForm,
      bmr: calculatedBMR,
      dailyCalories: dailyCalories,
      macros: calculateMacros(dailyCalories, profileForm.goal)
    };
    
    setUserProfile(profile);
    localStorage.setItem('userProfile', JSON.stringify(profile));
    setCurrentView('dashboard');
  };

  const calculateBMR = (profile) => {
    const { weight, height, age, gender } = profile;
    if (gender === 'male') {
      return 88.362 + (13.397 * parseFloat(weight)) + (4.799 * parseFloat(height)) - (5.677 * parseFloat(age));
    } else {
      return 447.593 + (9.247 * parseFloat(weight)) + (3.098 * parseFloat(height)) - (4.330 * parseFloat(age));
    }
  };

  const calculateDailyCalories = (bmr, activityLevel, goal) => {
    const activityMultipliers = {
      'sedentary': 1.2,
      'light': 1.375,
      'moderate': 1.55,
      'active': 1.725,
      'very-active': 1.9
    };
    
    const goalAdjustments = {
      'lose': -500,
      'maintain': 0,
      'gain': 500
    };
    
    return Math.round(bmr * activityMultipliers[activityLevel] + goalAdjustments[goal]);
  };

  const calculateMacros = (calories, goal) => {
    let proteinRatio, carbRatio, fatRatio;
    
    switch (goal) {
      case 'lose':
        proteinRatio = 0.35;
        carbRatio = 0.35;
        fatRatio = 0.30;
        break;
      case 'gain':
        proteinRatio = 0.25;
        carbRatio = 0.45;
        fatRatio = 0.30;
        break;
      default:
        proteinRatio = 0.30;
        carbRatio = 0.40;
        fatRatio = 0.30;
    }
    
    return {
      protein: Math.round((calories * proteinRatio) / 4),
      carbs: Math.round((calories * carbRatio) / 4),
      fat: Math.round((calories * fatRatio) / 9)
    };
  };

  // Food detection simulation
  const analyzeImage = async (file) => {
    setIsAnalyzing(true);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Mock food detection results
    const detectedFoods = [
      'Apple', 'Banana', 'Chicken Breast', 'Broccoli', 'Eggs'
    ];
    
    const randomFoods = detectedFoods.sort(() => 0.5 - Math.random()).slice(0, Math.floor(Math.random() * 3) + 1);
    
    randomFoods.forEach(foodName => {
      const newItem = {
        id: Date.now() + Math.random(),
        name: foodName,
        addedAt: new Date().toISOString(),
        detectedFromImage: true
      };
      setFridgeItems(prev => {
        const updated = [...prev, newItem];
        localStorage.setItem('fridgeItems', JSON.stringify(updated));
        return updated;
      });
    });
    
    setIsAnalyzing(false);
    setShowImageUpload(false);
  };

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      analyzeImage(file);
    }
  };

  const addFridgeItem = () => {
    if (newFridgeItem.trim()) {
      const newItem = {
        id: Date.now(),
        name: newFridgeItem.trim(),
        addedAt: new Date().toISOString()
      };
      const updatedFridge = [...fridgeItems, newItem];
      setFridgeItems(updatedFridge);
      localStorage.setItem('fridgeItems', JSON.stringify(updatedFridge));
      setNewFridgeItem('');
    }
  };

  const removeFridgeItem = (id) => {
    const updatedFridge = fridgeItems.filter(item => item.id !== id);
    setFridgeItems(updatedFridge);
    localStorage.setItem('fridgeItems', JSON.stringify(updatedFridge));
  };

  const addWater = () => {
    const newWaterIntake = waterIntake + 1;
    setWaterIntake(newWaterIntake);
    localStorage.setItem('waterIntake', newWaterIntake.toString());
  };

  const generateMealSuggestions = () => {
    const availableIngredients = fridgeItems.map(item => item.name.toLowerCase());
    const suggestions = foodDatabase.filter(food => 
      availableIngredients.some(ingredient => 
        food.name.toLowerCase().includes(ingredient) || 
        ingredient.includes(food.name.toLowerCase())
      )
    );
    
    if (suggestions.length === 0) {
      return foodDatabase.slice(0, 5);
    }
    
    return suggestions.slice(0, 5);
  };

  const createMealPlan = () => {
    const suggestions = generateMealSuggestions();
    const newMeal = {
      id: Date.now(),
      name: `Meal Plan ${mealPlan.length + 1}`,
      ingredients: suggestions.slice(0, 3),
      totalCalories: suggestions.slice(0, 3).reduce((sum, food) => sum + food.calories, 0),
      totalProtein: suggestions.slice(0, 3).reduce((sum, food) => sum + food.protein, 0),
      totalCarbs: suggestions.slice(0, 3).reduce((sum, food) => sum + food.carbs, 0),
      totalFat: suggestions.slice(0, 3).reduce((sum, food) => sum + food.fat, 0),
      createdAt: new Date().toISOString()
    };
    
    setMealPlan([...mealPlan, newMeal]);
  };

  const logout = () => {
    localStorage.removeItem('bodariUser');
    localStorage.removeItem('userProfile');
    localStorage.removeItem('fridgeItems');
    localStorage.removeItem('dailyProgress');
    localStorage.removeItem('waterIntake');
    setUser(null);
    setUserProfile(null);
    setFridgeItems([]);
    setMealPlan([]);
    setDailyProgress({ calories: 0, protein: 0, carbs: 0, fat: 0 });
    setWaterIntake(0);
    setCurrentView('auth');
  };

  // Navigation Component
  const Navigation = () => (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-2 md:left-0 md:top-0 md:bottom-0 md:w-64 md:border-r md:border-t-0">
      <div className="flex justify-around md:flex-col md:space-y-2 md:pt-4">
        <button
          onClick={() => setActiveTab('home')}
          className={`flex flex-col items-center p-2 rounded-lg transition-colors md:flex-row md:justify-start md:space-x-3 ${
            activeTab === 'home' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:text-blue-600'
          }`}
        >
          <Home size={24} />
          <span className="text-xs mt-1 md:text-sm md:mt-0">Home</span>
        </button>
        
        <button
          onClick={() => setActiveTab('meals')}
          className={`flex flex-col items-center p-2 rounded-lg transition-colors md:flex-row md:justify-start md:space-x-3 ${
            activeTab === 'meals' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:text-blue-600'
          }`}
        >
          <ChefHat size={24} />
          <span className="text-xs mt-1 md:text-sm md:mt-0">Meals</span>
        </button>
        
        <button
          onClick={() => setActiveTab('workouts')}
          className={`flex flex-col items-center p-2 rounded-lg transition-colors md:flex-row md:justify-start md:space-x-3 ${
            activeTab === 'workouts' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:text-blue-600'
          }`}
        >
          <TrendingUp size={24} />
          <span className="text-xs mt-1 md:text-sm md:mt-0">Workouts</span>
        </button>
        
        <button
          onClick={() => setActiveTab('progress')}
          className={`flex flex-col items-center p-2 rounded-lg transition-colors md:flex-row md:justify-start md:space-x-3 ${
            activeTab === 'progress' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:text-blue-600'
          }`}
        >
          <Award size={24} />
          <span className="text-xs mt-1 md:text-sm md:mt-0">Progress</span>
        </button>
        
        <button
          onClick={() => setActiveTab('profile')}
          className={`flex flex-col items-center p-2 rounded-lg transition-colors md:flex-row md:justify-start md:space-x-3 ${
            activeTab === 'profile' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:text-blue-600'
          }`}
        >
          <User size={24} />
          <span className="text-xs mt-1 md:text-sm md:mt-0">Profile</span>
        </button>
      </div>
    </nav>
  );

  // Image Upload Modal
  const ImageUploadModal = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">Add Food with AI</h3>
          <button onClick={() => setShowImageUpload(false)}>
            <X size={24} />
          </button>
        </div>
        
        {isAnalyzing ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Analyzing your food...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-600">Take a photo or upload an image of your food, and our AI will detect what you have!</p>
            
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => cameraInputRef.current?.click()}
                className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 transition-colors"
              >
                <Camera size={32} className="text-gray-400 mb-2" />
                <span className="text-sm text-gray-600">Take Photo</span>
              </button>
              
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 transition-colors"
              >
                <Upload size={32} className="text-gray-400 mb-2" />
                <span className="text-sm text-gray-600">Upload Image</span>
              </button>
            </div>
            
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
            
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="camera"
              onChange={handleImageUpload}
              className="hidden"
            />
          </div>
        )}
      </div>
    </div>
  );

  // Auth View
  if (currentView === 'auth') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-8">
          <div className="text-center mb-8">
            <div className="bg-emerald-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-emerald-600">B</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-800">Bodari</h1>
            <p className="text-gray-600">Your AI-powered fitness companion</p>
          </div>
          
          <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setAuthMode('signin')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                authMode === 'signin' ? 'bg-white text-emerald-600 shadow-sm' : 'text-gray-600'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setAuthMode('signup')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                authMode === 'signup' ? 'bg-white text-emerald-600 shadow-sm' : 'text-gray-600'
              }`}
            >
              Sign Up
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <input
                type="email"
                placeholder="Email"
                value={authForm.email}
                onChange={(e) => setAuthForm({...authForm, email: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
            </div>
            
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                value={authForm.password}
                onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            
            {authMode === 'signup' && (
              <div>
                <input
                  type="password"
                  placeholder="Confirm Password"
                  value={authForm.confirmPassword}
                  onChange={(e) => setAuthForm({...authForm, confirmPassword: e.target.value})}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
            )}
            
            <button
              onClick={handleAuth}
              className="w-full bg-emerald-600 text-white py-3 rounded-lg font-medium hover:bg-emerald-700 transition-colors"
            >
              {authMode === 'signin' ? 'Sign In' : 'Create Account'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Profile Setup View
  if (currentView === 'profile-setup') {
    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-6">
            <div className="bg-emerald-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-emerald-600">B</span>
            </div>
            <h2 className="text-2xl font-bold text-gray-800">Let's personalize Bodari for you</h2>
          </div>
          
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
                <input
                  type="text"
                  value={profileForm.name}
                  onChange={(e) => setProfileForm({...profileForm, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                <input
                  type="number"
                  value={profileForm.age}
                  onChange={(e) => setProfileForm({...profileForm, age: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                <select
                  value={profileForm.gender}
                  onChange={(e) => setProfileForm({...profileForm, gender: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Height (cm)</label>
                <input
                  type="number"
                  value={profileForm.height}
                  onChange={(e) => setProfileForm({...profileForm, height: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Weight (kg)</label>
                <input
                  type="number"
                  value={profileForm.weight}
                  onChange={(e) => setProfileForm({...profileForm, weight: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Activity Level</label>
                <select
                  value={profileForm.activityLevel}
                  onChange={(e) => setProfileForm({...profileForm, activityLevel: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Select</option>
                  <option value="sedentary">Sedentary (little/no exercise)</option>
                  <option value="light">Light (1-3 days/week)</option>
                  <option value="moderate">Moderate (3-5 days/week)</option>
                  <option value="active">Active (6-7 days/week)</option>
                  <option value="very-active">Very Active (2x/day)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Goal</label>
                <select
                  value={profileForm.goal}
                  onChange={(e) => setProfileForm({...profileForm, goal: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Select</option>
                  <option value="lose">Lose Weight</option>
                  <option value="maintain">Maintain Weight</option>
                  <option value="gain">Gain Weight</option>
                </select>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Allergies/Dietary Restrictions</label>
              <textarea
                value={profileForm.allergies}
                onChange={(e) => setProfileForm({...profileForm, allergies: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                rows="3"
                placeholder="List any allergies or dietary restrictions..."
              />
            </div>
            
            <button
              onClick={handleProfileSetup}
              className="w-full bg-emerald-600 text-white py-3 rounded-lg font-medium hover:bg-emerald-700 transition-colors"
            >
              Complete Setup
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Main Dashboard Views
  const renderTabContent = () => {
    switch (activeTab) {
      case 'home':
        return (
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow-sm p-4">
                <div className="flex items-center">
                  <Target className="h-6 w-6 text-emerald-600" />
                  <div className="ml-3">
                    <p className="text-xs font-medium text-gray-500">Daily Calories</p>
                    <p className="text-lg font-bold text-gray-900">{userProfile?.dailyCalories}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm p-4">
                <div className="flex items-center">
                  <Calculator className="h-
