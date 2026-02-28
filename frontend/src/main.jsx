import React from "react";
import ReactDOM from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "./context/AuthContext";
import App from "./components/App";
import DentalChatbot from "./pages/DentalChatbot";
import AutoShopChatbot from "./pages/AutoShopChatbot";
import SalonChatbot from "./pages/SalonChatbot";
import MedicalOfficeChatbot from "./pages/MedicalOfficeChatbot";
import RestaurantChatbot from "./pages/RestaurantChatbot";
import "./index.css";

const publicRoutes = {
  "/dental-chatbot": DentalChatbot,
  "/auto-shop-chatbot": AutoShopChatbot,
  "/salon-booking-chatbot": SalonChatbot,
  "/medical-office-chatbot": MedicalOfficeChatbot,
  "/restaurant-chatbot": RestaurantChatbot,
};

const path = window.location.pathname;
const PublicPage = publicRoutes[path];

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HelmetProvider>
      {PublicPage ? (
        <PublicPage />
      ) : (
        <AuthProvider>
          <App />
        </AuthProvider>
      )}
    </HelmetProvider>
  </React.StrictMode>
);
