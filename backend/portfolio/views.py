from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DocumentForm
from .models import Document


@login_required
def document_list(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.owner = request.user
            document.save()
            form = DocumentForm()  # fresh blank form after a successful add
    else:
        form = DocumentForm()

    documents = Document.objects.filter(owner=request.user)

    context = {"documents": documents, "form": form}

    if request.htmx:
        # HTMX POST from the add-document form: return just the updated
        # list + a reset form, not the whole page.
        return render(request, "portfolio/_list_and_form.html", context)

    return render(request, "portfolio/list.html", context)


@login_required
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    if request.method == "POST":
        document.delete()

    if request.htmx:
        documents = Document.objects.filter(owner=request.user)
        return render(request, "portfolio/_document_list.html", {"documents": documents})

    return redirect("portfolio:document_list")
