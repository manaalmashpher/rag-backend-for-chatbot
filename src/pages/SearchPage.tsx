import React from "react";
import { useSearchParams } from "react-router-dom";
import SearchInterface from "../components/SearchInterface";

const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Search Documents
        </h1>
        <p className="text-gray-600">
          Find information across all your processed documents using natural
          language queries
        </p>
      </div>

      <div className="card">
        <SearchInterface initialQuery={initialQuery} />
      </div>
    </div>
  );
};

export default SearchPage;
