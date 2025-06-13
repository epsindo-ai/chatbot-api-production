#!/bin/bash
# Convenience wrapper for recreate_super_admin.py

cd /app

echo "🔧 Super Admin Management Tool"
echo "=============================="
echo ""
echo "Choose an option:"
echo "1. Recreate super admin (full replacement)"
echo "2. Reset super admin password only"
echo "3. Promote existing user to super admin"
echo "4. Force recreate (no confirmations)"
echo "5. Exit"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo "Starting super admin recreation..."
        python app/scripts/recreate_super_admin.py
        ;;
    2)
        echo "Starting password reset..."
        python app/scripts/recreate_super_admin.py --reset-password
        ;;
    3)
        echo "Starting user promotion..."
        python app/scripts/recreate_super_admin.py --promote
        ;;
    4)
        echo "⚠️  WARNING: Force mode will skip all confirmations!"
        read -p "Are you sure? Type 'YES' to continue: " confirm
        if [ "$confirm" = "YES" ]; then
            python app/scripts/recreate_super_admin.py --force
        else
            echo "Operation cancelled."
        fi
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac
