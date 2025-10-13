import React, { useState, useEffect } from 'react';
import { apiClient } from '../../services/api';
import type { CongressMember } from '../../types';

interface MemberAlertFormData {
  name: string;
  target_id: number;
  target_name: string;
}

interface MemberAlertFormProps {
  onDataChange: (data: Partial<MemberAlertFormData>) => void;
}

export const MemberAlertForm: React.FC<MemberAlertFormProps> = ({ onDataChange }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CongressMember[]>([]);
  const [selectedMember, setSelectedMember] = useState<CongressMember | null>(null);
  const [alertName, setAlertName] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const searchMembers = async (query: string) => {
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await apiClient.searchMembers(query, 1, 10);
      setSearchResults(response.items);
    } catch (error) {
      console.error('Failed to search members:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchMembers(searchQuery);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  useEffect(() => {
    if (selectedMember && alertName) {
      onDataChange({
        name: alertName,
        target_id: selectedMember.id,
        target_name: `${selectedMember.first_name} ${selectedMember.last_name}`,
      });
    } else {
      onDataChange({});
    }
  }, [selectedMember, alertName, onDataChange]);

  const handleMemberSelect = (member: CongressMember) => {
    setSelectedMember(member);
    setSearchQuery('');
    setSearchResults([]);
    
    // Auto-generate alert name if not set
    if (!alertName) {
      const memberName = `${member.first_name} ${member.last_name}`;
      setAlertName(`${memberName} Trade Alert`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Member Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Congress Member
        </label>
        
        {selectedMember ? (
          <div className="flex items-center space-x-4 p-4 border border-gray-300 rounded-lg bg-gray-50">
            <div className="w-12 h-12 bg-gray-300 rounded-full flex items-center justify-center">
              <span className="text-lg font-bold text-gray-600">
                {selectedMember.first_name[0]}{selectedMember.last_name[0]}
              </span>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">
                {selectedMember.first_name} {selectedMember.last_name}
              </h3>
              <p className="text-sm text-gray-600">
                {selectedMember.party} - {selectedMember.state}
              </p>
            </div>
            <button
              onClick={() => setSelectedMember(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for a congress member..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            
            {isSearching && (
              <div className="absolute right-3 top-2.5">
                <div className="animate-spin h-5 w-5 border-2 border-primary-500 border-t-transparent rounded-full"></div>
              </div>
            )}
            
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-300 rounded-lg mt-1 max-h-64 overflow-y-auto z-10 shadow-lg">
                {searchResults.map((member) => (
                  <button
                    key={member.id}
                    onClick={() => handleMemberSelect(member)}
                    className="w-full flex items-center space-x-3 p-3 hover:bg-gray-50 text-left"
                  >
                    <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-gray-600">
                        {member.first_name[0]}{member.last_name[0]}
                      </span>
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">
                        {member.first_name} {member.last_name}
                      </div>
                      <div className="text-sm text-gray-600">
                        {member.party} - {member.state}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Alert Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Alert Name
        </label>
        <input
          type="text"
          value={alertName}
          onChange={(e) => setAlertName(e.target.value)}
          placeholder="Enter a name for this alert"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
        <p className="text-sm text-gray-500 mt-1">
          Give your alert a descriptive name so you can easily identify it
        </p>
      </div>

      {/* Preview */}
      {selectedMember && alertName && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">Alert Preview</h4>
          <p className="text-blue-800">
            You will receive notifications whenever{' '}
            <span className="font-semibold">
              {selectedMember.first_name} {selectedMember.last_name}
            </span>{' '}
            files new trade disclosures.
          </p>
        </div>
      )}
    </div>
  );
};
