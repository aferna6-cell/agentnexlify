import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "./context/AuthContext";
import App from "./components/App";
import DentalChatbot from "./pages/DentalChatbot";
import AutoShopChatbot from "./pages/AutoShopChatbot";
import SalonChatbot from "./pages/SalonChatbot";
import MedicalOfficeChatbot from "./pages/MedicalOfficeChatbot";
import RestaurantChatbot from "./pages/RestaurantChatbot";
import Home from "./pages/Home";
import FreeWidget from "./pages/FreeWidget";
import SignupPage from "./pages/SignupPage";
import IntercomAlternative from "./pages/IntercomAlternative";
import LiveChatAlternative from "./pages/LiveChatAlternative";
import TidioAlternative from "./pages/TidioAlternative";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/free-widget" element={<FreeWidget />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/dental-chatbot" element={<DentalChatbot />} />
          <Route path="/auto-shop-chatbot" element={<AutoShopChatbot />} />
          <Route path="/salon-booking-chatbot" element={<SalonChatbot />} />
          <Route path="/medical-office-chatbot" element={<MedicalOfficeChatbot />} />
          <Route path="/restaurant-chatbot" element={<RestaurantChatbot />} />
          <Route path="/intercom-alternative" element={<IntercomAlternative />} />
          <Route path="/livechat-alternative" element={<LiveChatAlternative />} />
          <Route path="/tidio-alternative" element={<TidioAlternative />} />
          <Route path="*" element={<AuthProvider><App /></AuthProvider>} />
        </Routes>
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
);
