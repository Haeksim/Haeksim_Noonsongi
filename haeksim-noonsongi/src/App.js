import logo from "./logo.png";
import "./App.css";

import { PayloadProvider } from "./context/PayloadContext";
import Header from "./component/Header";
import Body from "./component/Body";
import Footer from "./component/Footer";

function App() {
  return (
    <PayloadProvider>
      <div className="App">
        <Header />
        <Body />
        <Footer />
      </div>
    </PayloadProvider>
  );
}

export default App;
