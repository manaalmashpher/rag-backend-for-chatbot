import React from "react";
import { Link } from "react-router-dom";
import { Upload, BarChart3, Search, FileText } from "lucide-react";

const HomePage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to IonologyBot
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Upload, process, and search your documents with AI-powered analysis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Upload Card */}
        <div className="card text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-blue-100 rounded-full">
              <Upload className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Upload Documents
          </h3>
          <p className="text-gray-600 mb-4">
            Upload PDF, DOCX, TXT, or MD files for processing and indexing
          </p>
          <Link to="/upload" className="btn btn-primary">
            Start Uploading
          </Link>
        </div>

        {/* Status Card */}
        <div className="card text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-green-100 rounded-full">
              <BarChart3 className="h-8 w-8 text-green-600" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Check Status
          </h3>
          <p className="text-gray-600 mb-4">
            Monitor the processing status of your uploaded documents
          </p>
          <Link to="/status" className="btn btn-primary">
            View Status
          </Link>
        </div>

        {/* Search Card */}
        <div className="card text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-purple-100 rounded-full">
              <Search className="h-8 w-8 text-purple-600" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Search Documents
          </h3>
          <p className="text-gray-600 mb-4">
            Find information across all your processed documents
          </p>
          <Link to="/search" className="btn btn-primary">
            Start Searching
          </Link>
        </div>
      </div>

      <div className="mt-12 text-center">
        <div className="bg-white rounded-lg shadow p-8">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">1. Upload</h3>
              <p className="text-gray-600">
                Upload your documents and choose a chunking method for optimal
                processing
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">2. Process</h3>
              <p className="text-gray-600">
                Our system extracts text, creates embeddings, and indexes your
                content
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">3. Search</h3>
              <p className="text-gray-600">
                Use natural language queries to find relevant information across
                all documents
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
