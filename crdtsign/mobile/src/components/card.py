import flet as ft
import uuid


class ExpandableCard:
    def __init__(self, title: str, card_stack):
        self.id = str(uuid.uuid4())  # Unique identifier for each card
        self.title = title
        self.expanded = False
        self.expand_icon = ft.Icon(ft.Icons.EXPAND_MORE)
        self.collapse_icon = ft.Icon(ft.Icons.EXPAND_LESS)
        self.card_stack = card_stack  # Reference to parent CardStack for deletion
        self.card = self.create_card()

    def toggle_expand(self, e):
        self.expanded = not self.expanded
        self.update_card()
        e.page.update()

    def delete_card(self, e):
        """Show confirmation dialog and delete card if confirmed"""
        def on_confirm_delete(e):
            # Remove card from stack by ID
            self.delete_task(self)

        def on_cancel_delete(e):
            dlg.open = False
            e.page.update()

        # Create confirmation dialog
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Are you sure you want to delete '{self.title}'? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel_delete),
                ft.TextButton("Delete", on_click=on_confirm_delete, style=ft.ButtonStyle(color=ft.CupertinoColors.SYSTEM_RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        e.page.open(dlg)

    def delete_task(self, card):
        self.card_stack.remove_card_by_id(card.id)
        self.card_stack.page.clear()
        self.card_stack.page.update()

    def update_card(self):
        # Update the icon based on expanded state
        if self.expanded:
            self.expand_icon.icon = ft.Icons.EXPAND_LESS
        else:
            self.expand_icon.icon = ft.Icons.EXPAND_MORE

        # Rebuild the card content
        self.card.content = self.build_card_content()

    def build_card_content(self):
        base_content = [
            ft.CupertinoListTile(
                title=ft.Text(self.title),
                subtitle=ft.Text("Subtitle <123456>"),
                trailing=ft.IconButton(
                    icon=ft.Icons.EXPAND_MORE,
                    on_click=self.toggle_expand,
                    icon_size=20,
                ),
            ),
            ft.Text("Other text"),
        ]

        if self.expanded:
            base_content.extend([
                ft.Divider(),
                ft.Text("Additional Information:", weight=ft.FontWeight.BOLD),
                ft.Text("• This is expanded content"),
                ft.Text("• You can add more details here"),
                ft.Text("• Or any other information you want to show"),
                ft.Row([
                    ft.CupertinoButton(
                        content=ft.Text("Delete"),
                        color=ft.CupertinoColors.SYSTEM_RED,
                        on_click=self.delete_card,
                    ),
                    ft.CupertinoButton(
                        content=ft.Text("Verify Signature"),
                        color=ft.CupertinoColors.SYSTEM_GREEN,
                    ),
                ], alignment=ft.MainAxisAlignment.END, expand=True),
                ft.Container(height=10),  # Spacing
            ])

        return ft.Container(
            content=ft.Column(base_content, spacing=5),
            padding=10,
        )

    def create_card(self):
        return ft.Card(self.build_card_content())


class CardStack:
    def __init__(self, page: ft.Page):
        self.page = page
        self.cards = []  # Store ExpandableCard instances, not just cards
        self.stack = []  # This will be populated with the actual card widgets

        # Create cards and store both the instances and widgets
        for i in range(1, 11):
            card_instance = ExpandableCard(f"Card {i}", self)
            self.cards.append(card_instance)
            self.stack.append(card_instance.card)

    def remove_card_by_id(self, card_id: str):
        """Remove a card from the stack by its ID"""
        # Find the card instance with the matching ID
        card_to_remove = None
        for card in self.cards:
            if card.id == card_id:
                card_to_remove = card
                break

        if card_to_remove:
            # Remove from both lists
            self.cards.remove(card_to_remove)
            self.stack.remove(card_to_remove.card)

            # Update the UI by triggering a page update
            # The parent container will automatically reflect the changes
            self.page.update()
